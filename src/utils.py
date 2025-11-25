"""
Utility Functions
Provides logging, output formatting, and helper utilities
"""

import logging
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.config import Config

def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_to_console: bool = True
) -> None:
    """
    Set up logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        log_to_console: Whether to log to console
    """
    level = log_level or Config.LOG_LEVEL
    log_file = log_file or Config.LOG_FILE

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Add file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

    logging.info(f"Logging initialized at {level} level")

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def print_banner(text: str, char: str = "=") -> None:
    """
    Print a formatted banner

    Args:
        text: Banner text
        char: Character to use for banner border
    """
    border = char * (len(text) + 4)
    print(f"\n{border}")
    print(f"{char} {text} {char}")
    print(f"{border}\n")

def print_section(title: str) -> None:
    """
    Print a formatted section header

    Args:
        title: Section title
    """
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")

def print_subsection(title: str) -> None:
    """
    Print a formatted subsection header

    Args:
        title: Subsection title
    """
    print(f"\n{'-'*60}")
    print(f"{title}")
    print(f"{'-'*60}\n")

def print_key_value(key: str, value: Any, indent: int = 0) -> None:
    """
    Print a key-value pair with formatting

    Args:
        key: Key name
        value: Value
        indent: Indentation level
    """
    indent_str = "  " * indent
    print(f"{indent_str}{key}: {value}")

def print_list(items: List[str], bullet: str = "•", indent: int = 0) -> None:
    """
    Print a formatted list

    Args:
        items: List of items
        bullet: Bullet character
        indent: Indentation level
    """
    indent_str = "  " * indent
    for item in items:
        print(f"{indent_str}{bullet} {item}")

def save_json(data: Dict, file_path: Path, indent: int = 2) -> None:
    """
    Save data to JSON file

    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    logging.info(f"Saved JSON to: {file_path}")

def load_json(file_path: Path) -> Dict:
    """
    Load data from JSON file

    Args:
        file_path: Input file path

    Returns:
        Loaded data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logging.info(f"Loaded JSON from: {file_path}")
    return data

def generate_report(
    title: str,
    sections: Dict[str, Any],
    output_path: Optional[Path] = None
) -> str:
    """
    Generate a formatted text report

    Args:
        title: Report title
        sections: Dictionary of section names and content
        output_path: Optional path to save report

    Returns:
        Formatted report text
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"{title.center(80)}")
    lines.append("=" * 80)
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    for section_name, content in sections.items():
        lines.append("-" * 80)
        lines.append(f"{section_name}")
        lines.append("-" * 80)

        if isinstance(content, dict):
            for key, value in content.items():
                lines.append(f"{key}: {value}")
        elif isinstance(content, list):
            for item in content:
                lines.append(f"  • {item}")
        else:
            lines.append(str(content))

        lines.append("")

    report = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logging.info(f"Report saved to: {output_path}")

    return report

def create_summary_table(
    headers: List[str],
    rows: List[List[str]],
    markdown: bool = True
) -> str:
    """
    Create a formatted table

    Args:
        headers: Column headers
        rows: Table rows
        markdown: Whether to use markdown format

    Returns:
        Formatted table string
    """
    if markdown:
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join([" --- " for _ in headers]) + "|")

        for row in rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        return "\n".join(lines)
    else:
        # Simple text table
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        lines = []

        # Header
        header_line = " | ".join(
            headers[i].ljust(col_widths[i]) for i in range(len(headers))
        )
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # Rows
        for row in rows:
            row_line = " | ".join(
                str(row[i]).ljust(col_widths[i]) for i in range(len(row))
            )
            lines.append(row_line)

        return "\n".join(lines)

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to append if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't

    Args:
        path: Directory path

    Returns:
        Directory path
    """
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_timestamp(format: str = "%Y%m%d_%H%M%S") -> str:
    """
    Get current timestamp as formatted string

    Args:
        format: Timestamp format

    Returns:
        Formatted timestamp
    """
    return datetime.now().strftime(format)

class ProgressTracker:
    """Simple progress tracker for batch operations"""

    def __init__(self, total: int, description: str = "Processing"):
        """
        Initialize progress tracker

        Args:
            total: Total number of items
            description: Progress description
        """
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()

    def update(self, increment: int = 1) -> None:
        """Update progress"""
        self.current += increment
        self._print_progress()

    def _print_progress(self) -> None:
        """Print current progress"""
        percentage = (self.current / self.total) * 100
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed if elapsed > 0 else 0

        print(
            f"\r{self.description}: {self.current}/{self.total} "
            f"({percentage:.1f}%) - {rate:.2f} items/sec",
            end=""
        )

        if self.current >= self.total:
            print()  # New line at completion

    def complete(self) -> None:
        """Mark as complete"""
        self.current = self.total
        self._print_progress()
