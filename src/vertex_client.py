"""
Vertex AI Client Wrapper
Handles file upload and content generation using Gemini models via Google Cloud Vertex AI
"""

import time
import logging
import base64
from pathlib import Path
from typing import Optional, Union, Any, List

import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from src.config import Config
from src.token_monitor import get_monitor

logger = logging.getLogger(__name__)

class VertexAIClient:
    """Wrapper for Vertex AI interactions using Gemini models"""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        enable_token_monitoring: bool = True
    ):
        """
        Initialize Vertex AI client

        Args:
            project_id: GCP project ID (uses Config.VERTEX_PROJECT_ID if not provided)
            location: GCP location (uses Config.VERTEX_LOCATION if not provided)
            enable_token_monitoring: Whether to enable token usage monitoring
        """
        self.project_id = project_id or Config.VERTEX_PROJECT_ID
        self.location = location or Config.VERTEX_LOCATION

        if not self.project_id:
            raise ValueError("Vertex AI project_id is required")

        if not self.location:
            raise ValueError("Vertex AI location is required")

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        self.model_name = Config.GEMINI_MODEL

        # Configure generation parameters for text format
        gen_config_params = {
            "temperature": Config.TEMPERATURE,
            "top_p": Config.TOP_P,
            "top_k": Config.TOP_K,
            "max_output_tokens": Config.MAX_OUTPUT_TOKENS,
        }

        self.generation_config = GenerationConfig(**gen_config_params)

        # Initialize the model
        self.model = GenerativeModel(self.model_name)

        # Initialize token monitoring
        self.enable_token_monitoring = enable_token_monitoring
        if self.enable_token_monitoring:
            self.token_monitor = get_monitor()
            logger.info("Token monitoring enabled")
        else:
            self.token_monitor = None

        logger.info(f"Initialized VertexAIClient with model: {self.model_name}")
        logger.info(f"Project: {self.project_id}, Location: {self.location}")

    def _load_file_as_part(self, file_path: Union[str, Path]) -> Part:
        """
        Load file and convert to Vertex AI Part object

        Args:
            file_path: Path to the file to load

        Returns:
            Part object for Vertex AI
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        mime_type = self._get_mime_type(file_path)

        with open(file_path, "rb") as f:
            file_data = f.read()

        return Part.from_data(data=file_data, mime_type=mime_type)

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
        Generate content with file using Vertex AI

        Args:
            file_path: Path to PDF or image file
            prompt: Prompt to send with the file
            wait_for_processing: Compatibility parameter (not used with Vertex AI)

        Returns:
            Generated text response
        """
        file_path = Path(file_path)

        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.info(f"Generating content for file: {file_path.name}")

                # Load file as Part
                file_part = self._load_file_as_part(file_path)

                # Create content parts: prompt + file
                contents = [prompt, file_part]

                # Generate content using Vertex AI
                response = self.model.generate_content(
                    contents,
                    generation_config=self.generation_config
                )

                # Extract text from response
                result = response.text
                logger.info(f"Content generated successfully ({len(result)} chars)")

                # Record token usage
                if self.enable_token_monitoring and hasattr(response, 'usage_metadata'):
                    usage = response.usage_metadata
                    self.token_monitor.record_usage(
                        model=self.model_name,
                        operation_type='file_generation',
                        prompt_tokens=usage.prompt_token_count,
                        completion_tokens=usage.candidates_token_count,
                        total_tokens=usage.total_token_count,
                        file_name=file_path.name,
                        prompt_preview=prompt
                    )
                    logger.info(f"Token usage: {usage.total_token_count} tokens "
                              f"(input: {usage.prompt_token_count}, "
                              f"output: {usage.candidates_token_count})")

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
        Generate content from text-only prompt

        Args:
            prompt: Text prompt to send

        Returns:
            Generated text response
        """
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.info(f"Generating content from text prompt ({len(prompt)} chars)")

                # Generate content using Vertex AI
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )

                result = response.text
                logger.info(f"Content generated successfully ({len(result)} chars)")

                # Record token usage
                if self.enable_token_monitoring and hasattr(response, 'usage_metadata'):
                    usage = response.usage_metadata
                    self.token_monitor.record_usage(
                        model=self.model_name,
                        operation_type='text_generation',
                        prompt_tokens=usage.prompt_token_count,
                        completion_tokens=usage.candidates_token_count,
                        total_tokens=usage.total_token_count,
                        prompt_preview=prompt
                    )
                    logger.info(f"Token usage: {usage.total_token_count} tokens "
                              f"(input: {usage.prompt_token_count}, "
                              f"output: {usage.candidates_token_count})")

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

    # Legacy compatibility methods (for compatibility with GeminiClient interface)
    def upload_file(self, file_path: Union[str, Path]) -> Any:
        """
        Legacy method for compatibility - not used with Vertex AI inline approach

        Args:
            file_path: Path to the file

        Returns:
            File path (for compatibility)
        """
        logger.warning("upload_file() is deprecated with Vertex AI - files are sent inline")
        return file_path

    def wait_for_file_processing(self, uploaded_file: Any, timeout: int = 300) -> bool:
        """
        Legacy method for compatibility - not needed with Vertex AI

        Args:
            uploaded_file: File reference
            timeout: Not used

        Returns:
            True (for compatibility)
        """
        logger.warning("wait_for_file_processing() is not needed with Vertex AI")
        return True

    def delete_file(self, file_name: str) -> None:
        """
        Legacy method for compatibility - not needed with Vertex AI

        Args:
            file_name: Name of the file
        """
        logger.warning("delete_file() is not needed with Vertex AI - files are not stored")

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
