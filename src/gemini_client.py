"""
Gemini API Client Wrapper using OpenAI SDK
Handles file upload and content generation using Gemini 2.0 via OpenAI-compatible API
"""

import time
import logging
import base64
from pathlib import Path
from typing import Optional, Union, Any, List
from openai import OpenAI

from src.config import Config
from src.token_monitor import get_monitor

logger = logging.getLogger(__name__)

class GeminiClient:
    """Wrapper for Gemini API interactions using OpenAI SDK"""

    def __init__(self, api_key: Optional[str] = None, enable_token_monitoring: bool = True):
        """
        Initialize Gemini client with OpenAI SDK

        Args:
            api_key: Gemini API key (uses Config.GEMINI_API_KEY if not provided)
            enable_token_monitoring: Whether to enable token usage monitoring
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        # Initialize OpenAI client with Gemini base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=Config.GEMINI_BASE_URL
        )
        
        self.model_name = Config.GEMINI_MODEL

        # Configure generation parameters
        self.generation_config = {
            "temperature": Config.TEMPERATURE,
            "top_p": Config.TOP_P,
            "max_tokens": Config.MAX_OUTPUT_TOKENS,
        }

        # Initialize token monitoring
        self.enable_token_monitoring = enable_token_monitoring
        if self.enable_token_monitoring:
            self.token_monitor = get_monitor()
            logger.info("Token monitoring enabled")
        else:
            self.token_monitor = None

        logger.info(f"Initialized GeminiClient with model: {self.model_name} via OpenAI SDK")
        logger.info(f"Base URL: {Config.GEMINI_BASE_URL}")

    def _encode_file_to_base64(self, file_path: Union[str, Path]) -> str:
        """
        Encode file to base64 string

        Args:
            file_path: Path to the file to encode

        Returns:
            Base64 encoded string
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _get_mime_type(self, file_path: Path) -> str:
        """
        Get MIME type for file

        Args:
            file_path: Path to the file

        Returns:
            MIME type string
        """
        suffix = file_path.suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
        }
        return mime_types.get(suffix, 'application/octet-stream')

    def generate_content_with_file(
        self,
        file_path: Union[str, Path],
        prompt: str,
        wait_for_processing: bool = True
    ) -> str:
        """
        Generate content with file using OpenAI SDK (Stage 1)

        Args:
            file_path: Path to PDF or image file
            prompt: Prompt to send with the file
            wait_for_processing: Compatibility parameter (not used with OpenAI SDK)

        Returns:
            Generated text response
        """
        file_path = Path(file_path)
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.info(f"Generating content for file: {file_path.name}")

                # Encode file to base64
                base64_file = self._encode_file_to_base64(file_path)
                mime_type = self._get_mime_type(file_path)

                # Create messages with file content
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_file}"
                                }
                            }
                        ]
                    }
                ]

                # Generate content using OpenAI SDK
                # No response format configuration needed for text format
                extra_params = {}

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **self.generation_config,
                    **extra_params
                )

                # Extract text from response
                result = response.choices[0].message.content
                logger.info(f"Content generated successfully ({len(result)} chars)")

                # Record token usage
                if self.enable_token_monitoring and hasattr(response, 'usage'):
                    self.token_monitor.record_usage(
                        model=self.model_name,
                        operation_type='file_generation',
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        file_name=file_path.name,
                        prompt_preview=prompt
                    )
                    logger.info(f"Token usage: {response.usage.total_tokens} tokens "
                              f"(input: {response.usage.prompt_tokens}, "
                              f"output: {response.usage.completion_tokens})")
                
                # Development logging: Log full LLM output
                logger.debug(f"LLM RAW OUTPUT START [{file_path.name}]")
                for line in result.split('\n'):
                    logger.debug(f"LLM: {line}")
                logger.debug(f"LLM RAW OUTPUT END [{file_path.name}]")

                return result

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{Config.MAX_RETRIES} failed: {str(e)}")

                if attempt < Config.MAX_RETRIES - 1:
                    delay = Config.RETRY_DELAY * (Config.RETRY_BACKOFF ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All retries exhausted for file: {file_path}")
                    raise

    def generate_content_from_text(self, prompt: str) -> str:
        """
        Generate content from text-only prompt (Stage 2)

        Args:
            prompt: Text prompt to send

        Returns:
            Generated text response
        """
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.info(f"Generating content from text prompt ({len(prompt)} chars)")

                # Create messages
                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                # Generate content using OpenAI SDK
                # No response format configuration needed for text format
                extra_params = {}

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **self.generation_config,
                    **extra_params
                )

                result = response.choices[0].message.content
                logger.info(f"Content generated successfully ({len(result)} chars)")

                # Record token usage
                if self.enable_token_monitoring and hasattr(response, 'usage'):
                    self.token_monitor.record_usage(
                        model=self.model_name,
                        operation_type='text_generation',
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        prompt_preview=prompt
                    )
                    logger.info(f"Token usage: {response.usage.total_tokens} tokens "
                              f"(input: {response.usage.prompt_tokens}, "
                              f"output: {response.usage.completion_tokens})")

                return result

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{Config.MAX_RETRIES} failed: {str(e)}")

                if attempt < Config.MAX_RETRIES - 1:
                    delay = Config.RETRY_DELAY * (Config.RETRY_BACKOFF ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("All retries exhausted for text generation")
                    raise

    # Legacy compatibility methods (no longer needed with OpenAI SDK)
    def upload_file(self, file_path: Union[str, Path]) -> Any:
        """
        Legacy method for compatibility - not used with OpenAI SDK
        
        Args:
            file_path: Path to the file
            
        Returns:
            File path (for compatibility)
        """
        logger.warning("upload_file() is deprecated with OpenAI SDK - files are sent inline")
        return file_path

    def wait_for_file_processing(self, uploaded_file: Any, timeout: int = 300) -> bool:
        """
        Legacy method for compatibility - not needed with OpenAI SDK
        
        Args:
            uploaded_file: File reference
            timeout: Not used
            
        Returns:
            True (for compatibility)
        """
        logger.warning("wait_for_file_processing() is not needed with OpenAI SDK")
        return True

    def delete_file(self, file_name: str) -> None:
        """
        Legacy method for compatibility - not needed with OpenAI SDK
        
        Args:
            file_name: Name of the file
        """
        logger.warning("delete_file() is not needed with OpenAI SDK - files are not stored")

    def get_token_stats(self) -> dict:
        """
        Get token usage statistics for current session
        
        Returns:
            Dictionary with token statistics
        """
        if self.enable_token_monitoring:
            return self.token_monitor.get_session_stats()
        return {}
    
    def print_token_summary(self):
        """Print token usage summary for current session"""
        if self.enable_token_monitoring:
            self.token_monitor.print_session_summary()
        else:
            logger.warning("Token monitoring is not enabled")

    def start_token_transaction(self, transaction_name: str):
        """Start tracking tokens for a specific transaction"""
        if self.enable_token_monitoring:
            self.token_monitor.start_transaction(transaction_name)

    def end_token_transaction(self) -> dict:
        """End current transaction and return token statistics"""
        if self.enable_token_monitoring:
            return self.token_monitor.end_transaction()
        return {}
