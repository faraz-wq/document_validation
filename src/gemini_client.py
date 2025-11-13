"""
Gemini API Client Wrapper
Handles file upload and content generation using Google Gemini 2.5
"""

import time
import logging
from pathlib import Path
from typing import Optional, Union
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from config import Config

logger = logging.getLogger(__name__)

class GeminiClient:
    """Wrapper for Google Gemini API interactions"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client

        Args:
            api_key: Gemini API key (uses Config.GEMINI_API_KEY if not provided)
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        genai.configure(api_key=self.api_key)
        self.model_name = Config.GEMINI_MODEL

        # Configure generation parameters
        self.generation_config = {
            "temperature": Config.TEMPERATURE,
            "top_p": Config.TOP_P,
            "top_k": Config.TOP_K,
            "max_output_tokens": Config.MAX_OUTPUT_TOKENS,
        }

        # Safety settings - minimal blocking for document processing
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        logger.info(f"Initialized GeminiClient with model: {self.model_name}")

    def upload_file(self, file_path: Union[str, Path]) -> genai.File:
        """
        Upload a file to Gemini API

        Args:
            file_path: Path to the file to upload

        Returns:
            Uploaded file object

        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: For API errors
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Uploading file to Gemini: {file_path.name}")

        try:
            uploaded_file = genai.upload_file(path=str(file_path))
            logger.info(f"File uploaded successfully: {uploaded_file.name}")
            return uploaded_file
        except Exception as e:
            logger.error(f"Error uploading file {file_path.name}: {str(e)}")
            raise

    def wait_for_file_processing(self, uploaded_file: genai.File, timeout: int = 300) -> bool:
        """
        Wait for uploaded file to be processed by Gemini

        Args:
            uploaded_file: Uploaded file object
            timeout: Maximum wait time in seconds

        Returns:
            True if file is processed successfully

        Raises:
            TimeoutError: If processing times out
            Exception: If processing fails
        """
        start_time = time.time()

        while uploaded_file.state.name == "PROCESSING":
            if time.time() - start_time > timeout:
                raise TimeoutError(f"File processing timeout after {timeout} seconds")

            logger.debug(f"Waiting for file processing: {uploaded_file.name}")
            time.sleep(2)
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise Exception(f"File processing failed: {uploaded_file.name}")

        logger.info(f"File processed successfully: {uploaded_file.name}")
        return True

    def generate_content_with_file(
        self,
        file_path: Union[str, Path],
        prompt: str,
        wait_for_processing: bool = True
    ) -> str:
        """
        Upload file and generate content with prompt (Stage 1)

        Args:
            file_path: Path to PDF or image file
            prompt: Prompt to send with the file
            wait_for_processing: Whether to wait for file processing

        Returns:
            Generated text response
        """
        for attempt in range(Config.MAX_RETRIES):
            try:
                # Upload file
                uploaded_file = self.upload_file(file_path)

                # Wait for processing if needed
                if wait_for_processing:
                    self.wait_for_file_processing(uploaded_file)

                # Generate content
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings
                )

                logger.info(f"Generating content for file: {Path(file_path).name}")
                response = model.generate_content([uploaded_file, prompt])

                # Extract text from response
                result = response.text
                logger.info(f"Content generated successfully ({len(result)} chars)")

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
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings
                )

                logger.info(f"Generating content from text prompt ({len(prompt)} chars)")
                response = model.generate_content(prompt)

                result = response.text
                logger.info(f"Content generated successfully ({len(result)} chars)")

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

    def delete_file(self, file_name: str) -> None:
        """
        Delete uploaded file from Gemini

        Args:
            file_name: Name of the file to delete
        """
        try:
            genai.delete_file(file_name)
            logger.info(f"Deleted file: {file_name}")
        except Exception as e:
            logger.warning(f"Error deleting file {file_name}: {str(e)}")
