"""
Token Usage Monitoring System
Tracks input/output tokens, costs, and provides analytics
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Single token usage record"""
    timestamp: str
    model: str
    operation_type: str  # 'file_generation' or 'text_generation'
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    file_name: Optional[str] = None
    prompt_preview: Optional[str] = None  # First 100 chars of prompt
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @property
    def estimated_cost(self) -> float:
        """
        Estimate cost based on model pricing
        Prices as of Nov 2025 (update as needed)
        """
        # Gemini 2.0 Flash pricing (per 1M tokens)
        pricing = {
            'gemini-2.5-pro-exp': {
                'input': 0.0,  # Free during preview
                'output': 0.0
            },
            'gemini-2.5-pro': {
                'input': 0.0,  # Free during preview
                'output': 0.0
            },
            'gemini-1.5-flash': {
                'input': 0.075,  # $0.075 per 1M tokens
                'output': 0.30   # $0.30 per 1M tokens
            },
            'gemini-1.5-pro': {
                'input': 1.25,   # $1.25 per 1M tokens
                'output': 5.00   # $5.00 per 1M tokens
            }
        }
        
        model_pricing = pricing.get(self.model, {'input': 0.0, 'output': 0.0})
        input_cost = (self.prompt_tokens / 1_000_000) * model_pricing['input']
        output_cost = (self.completion_tokens / 1_000_000) * model_pricing['output']
        
        return input_cost + output_cost


class TokenMonitor:
    """Monitor and track token usage across API calls"""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize token monitor

        Args:
            storage_path: Path to store token usage logs (default: outputs/token_usage.jsonl)
        """
        if storage_path is None:
            from src.config import Config
            storage_path = Config.OUTPUTS_DIR / "token_usage.jsonl"

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache for current session
        self.session_usage: List[TokenUsage] = []

        # Track tokens for current transaction (e.g., processing one certificate type)
        self.current_transaction: Optional[str] = None  # Certificate type name
        self.transaction_usage: List[TokenUsage] = []    # Usage for current transaction

        logger.info(f"TokenMonitor initialized, logging to: {self.storage_path}")

    def start_transaction(self, transaction_name: str):
        """
        Start tracking tokens for a specific transaction (e.g., processing one certificate type)

        Args:
            transaction_name: Name of the transaction (e.g., certificate type)
        """
        self.current_transaction = transaction_name
        self.transaction_usage = []
        logger.info(f"Started tracking tokens for transaction: {transaction_name}")

    def end_transaction(self) -> Dict:
        """
        End current transaction and return token statistics for it

        Returns:
            Dictionary with transaction token statistics
        """
        if not self.current_transaction:
            logger.warning("No active transaction to end")
            return {
                'transaction_name': None,
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'estimated_cost': 0.0,
                'api_calls': 0
            }

        total_prompt = sum(u.prompt_tokens for u in self.transaction_usage)
        total_completion = sum(u.completion_tokens for u in self.transaction_usage)
        total_tokens = sum(u.total_tokens for u in self.transaction_usage)
        total_cost = sum(u.estimated_cost for u in self.transaction_usage)
        api_calls = len(self.transaction_usage)

        transaction_stats = {
            'transaction_name': self.current_transaction,
            'total_tokens': total_tokens,
            'total_prompt_tokens': total_prompt,
            'total_completion_tokens': total_completion,
            'estimated_cost': total_cost,
            'api_calls': api_calls
        }

        logger.info(f"Completed transaction '{self.current_transaction}': "
                   f"{total_tokens} tokens ({total_prompt} input, {total_completion} output), "
                   f"estimated cost: ${total_cost:.4f}")

        # Reset transaction tracking
        self.current_transaction = None
        self.transaction_usage = []

        return transaction_stats

    def record_usage(
        self,
        model: str,
        operation_type: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        file_name: Optional[str] = None,
        prompt_preview: Optional[str] = None
    ) -> TokenUsage:
        """
        Record a token usage event
        
        Args:
            model: Model name used
            operation_type: Type of operation ('file_generation' or 'text_generation')
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            total_tokens: Total tokens used
            file_name: Optional file name being processed
            prompt_preview: Optional preview of the prompt
            
        Returns:
            TokenUsage object
        """
        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            model=model,
            operation_type=operation_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            file_name=file_name,
            prompt_preview=prompt_preview[:100] if prompt_preview else None
        )
        
        # Add to session cache
        self.session_usage.append(usage)

        # Add to transaction cache if transaction is active
        if self.current_transaction is not None:
            self.transaction_usage.append(usage)

        # Persist to file (JSONL format - one JSON object per line)
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(usage.to_dict()) + '\n')
            logger.debug(f"Recorded token usage: {total_tokens} tokens ({model})")
        except Exception as e:
            logger.error(f"Failed to persist token usage: {e}")

        return usage
    
    def get_session_stats(self) -> Dict:
        """
        Get statistics for current session
        
        Returns:
            Dictionary with session statistics
        """
        if not self.session_usage:
            return {
                'total_calls': 0,
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'estimated_cost': 0.0,
                'by_operation': {},
                'by_model': {}
            }
        
        total_prompt = sum(u.prompt_tokens for u in self.session_usage)
        total_completion = sum(u.completion_tokens for u in self.session_usage)
        total_tokens = sum(u.total_tokens for u in self.session_usage)
        total_cost = sum(u.estimated_cost for u in self.session_usage)
        
        # Group by operation type
        by_operation = defaultdict(lambda: {'calls': 0, 'tokens': 0})
        for usage in self.session_usage:
            by_operation[usage.operation_type]['calls'] += 1
            by_operation[usage.operation_type]['tokens'] += usage.total_tokens
        
        # Group by model
        by_model = defaultdict(lambda: {'calls': 0, 'tokens': 0})
        for usage in self.session_usage:
            by_model[usage.model]['calls'] += 1
            by_model[usage.model]['tokens'] += usage.total_tokens
        
        return {
            'total_calls': len(self.session_usage),
            'total_tokens': total_tokens,
            'total_prompt_tokens': total_prompt,
            'total_completion_tokens': total_completion,
            'estimated_cost': total_cost,
            'by_operation': dict(by_operation),
            'by_model': dict(by_model)
        }
    
    def get_all_time_stats(self) -> Dict:
        """
        Get statistics for all recorded usage
        
        Returns:
            Dictionary with all-time statistics
        """
        all_usage = self._load_all_usage()
        
        if not all_usage:
            return {
                'total_calls': 0,
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'estimated_cost': 0.0,
                'by_operation': {},
                'by_model': {},
                'by_date': {}
            }
        
        total_prompt = sum(u.prompt_tokens for u in all_usage)
        total_completion = sum(u.completion_tokens for u in all_usage)
        total_tokens = sum(u.total_tokens for u in all_usage)
        total_cost = sum(u.estimated_cost for u in all_usage)
        
        # Group by operation type
        by_operation = defaultdict(lambda: {'calls': 0, 'tokens': 0, 'cost': 0.0})
        for usage in all_usage:
            by_operation[usage.operation_type]['calls'] += 1
            by_operation[usage.operation_type]['tokens'] += usage.total_tokens
            by_operation[usage.operation_type]['cost'] += usage.estimated_cost
        
        # Group by model
        by_model = defaultdict(lambda: {'calls': 0, 'tokens': 0, 'cost': 0.0})
        for usage in all_usage:
            by_model[usage.model]['calls'] += 1
            by_model[usage.model]['tokens'] += usage.total_tokens
            by_model[usage.model]['cost'] += usage.estimated_cost
        
        # Group by date
        by_date = defaultdict(lambda: {'calls': 0, 'tokens': 0, 'cost': 0.0})
        for usage in all_usage:
            date = usage.timestamp.split('T')[0]  # Extract date part
            by_date[date]['calls'] += 1
            by_date[date]['tokens'] += usage.total_tokens
            by_date[date]['cost'] += usage.estimated_cost
        
        return {
            'total_calls': len(all_usage),
            'total_tokens': total_tokens,
            'total_prompt_tokens': total_prompt,
            'total_completion_tokens': total_completion,
            'estimated_cost': total_cost,
            'by_operation': dict(by_operation),
            'by_model': dict(by_model),
            'by_date': dict(sorted(by_date.items()))
        }
    
    def _load_all_usage(self) -> List[TokenUsage]:
        """
        Load all usage records from storage
        
        Returns:
            List of TokenUsage objects
        """
        if not self.storage_path.exists():
            return []
        
        usage_list = []
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        usage_list.append(TokenUsage(**data))
        except Exception as e:
            logger.error(f"Failed to load token usage history: {e}")
        
        return usage_list
    
    def print_session_summary(self):
        """Print a formatted summary of session statistics"""
        stats = self.get_session_stats()
        
        print("\n" + "="*60)
        print("TOKEN USAGE - CURRENT SESSION")
        print("="*60)
        print(f"Total API Calls: {stats['total_calls']}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"  - Input Tokens: {stats['total_prompt_tokens']:,}")
        print(f"  - Output Tokens: {stats['total_completion_tokens']:,}")
        print(f"Estimated Cost: ${stats['estimated_cost']:.4f}")
        
        if stats['by_operation']:
            print("\nBy Operation Type:")
            for op_type, data in stats['by_operation'].items():
                print(f"  {op_type}: {data['calls']} calls, {data['tokens']:,} tokens")
        
        if stats['by_model']:
            print("\nBy Model:")
            for model, data in stats['by_model'].items():
                print(f"  {model}: {data['calls']} calls, {data['tokens']:,} tokens")
        
        print("="*60 + "\n")
    
    def print_all_time_summary(self):
        """Print a formatted summary of all-time statistics"""
        stats = self.get_all_time_stats()
        
        print("\n" + "="*60)
        print("TOKEN USAGE - ALL TIME")
        print("="*60)
        print(f"Total API Calls: {stats['total_calls']}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"  - Input Tokens: {stats['total_prompt_tokens']:,}")
        print(f"  - Output Tokens: {stats['total_completion_tokens']:,}")
        print(f"Estimated Cost: ${stats['estimated_cost']:.4f}")
        
        if stats['by_operation']:
            print("\nBy Operation Type:")
            for op_type, data in stats['by_operation'].items():
                print(f"  {op_type}:")
                print(f"    Calls: {data['calls']}, Tokens: {data['tokens']:,}, Cost: ${data['cost']:.4f}")
        
        if stats['by_model']:
            print("\nBy Model:")
            for model, data in stats['by_model'].items():
                print(f"  {model}:")
                print(f"    Calls: {data['calls']}, Tokens: {data['tokens']:,}, Cost: ${data['cost']:.4f}")
        
        if stats['by_date']:
            print("\nBy Date (last 7 days):")
            dates = list(stats['by_date'].items())[-7:]  # Last 7 days
            for date, data in dates:
                print(f"  {date}: {data['calls']} calls, {data['tokens']:,} tokens, ${data['cost']:.4f}")
        
        print("="*60 + "\n")
    
    def export_to_csv(self, output_path: Optional[Path] = None) -> Path:
        """
        Export all usage data to CSV
        
        Args:
            output_path: Path for CSV file (default: outputs/token_usage.csv)
            
        Returns:
            Path to created CSV file
        """
        if output_path is None:
            from src.config import Config
            output_path = Config.OUTPUTS_DIR / "token_usage.csv"
        
        output_path = Path(output_path)
        all_usage = self._load_all_usage()
        
        import csv
        with open(output_path, 'w', newline='') as f:
            if all_usage:
                writer = csv.DictWriter(f, fieldnames=all_usage[0].to_dict().keys())
                writer.writeheader()
                for usage in all_usage:
                    row = usage.to_dict()
                    row['estimated_cost'] = usage.estimated_cost
                    writer.writerow(row)
        
        logger.info(f"Exported token usage to: {output_path}")
        return output_path


# Global instance for easy access
_global_monitor: Optional[TokenMonitor] = None


def get_monitor() -> TokenMonitor:
    """Get or create global token monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = TokenMonitor()
    return _global_monitor
