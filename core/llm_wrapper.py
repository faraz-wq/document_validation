"""
OpenAI-compatible LLM wrapper.

Provides a single reusable function for all LLM calls with:
- Support for any OpenAI-compatible API (OpenAI, Azure, Together AI, Ollama, etc.)
- Retry logic with exponential backoff
- Defensive JSON parsing
- Error handling and logging
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass


def llm_call(
    messages: List[Dict[str, str]],
    json_mode: bool = True,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Dict[str, Any]:
    """
    Call OpenAI-compatible LLM API.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
                 Example: [{"role": "user", "content": "Hello"}]
        json_mode: If True, enforce JSON output format
        temperature: Sampling temperature (0.0 = deterministic)
        max_tokens: Maximum tokens in response
        retry_count: Number of retries on failure
        retry_delay: Initial delay between retries (exponential backoff)
        
    Returns:
        Parsed JSON response (if json_mode=True) or string response
        
    Raises:
        LLMError: On API errors after all retries exhausted
        
    Examples:
        >>> messages = [{"role": "user", "content": "Say hello in JSON"}]
        >>> result = llm_call(messages, json_mode=True)
        >>> print(result)
        {"message": "hello"}
    """
    # Create OpenAI client with custom base URL
    client = OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY
    )
    
    # Prepare request parameters
    request_params = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    # Enable JSON mode if requested
    if json_mode:
        request_params["response_format"] = {"type": "json_object"}
    
    # Log request (at DEBUG level)
    logger.debug(f"LLM Request: model={settings.LLM_MODEL}, messages={len(messages)} messages")
    logger.debug(f"Request params: {request_params}")
    
    # Retry loop
    last_error = None
    for attempt in range(retry_count):
        try:
            # Make API call
            response = client.chat.completions.create(**request_params)
            
            # Extract content
            content = response.choices[0].message.content
            
            # Handle None content
            if content is None:
                content = ""
            
            # Log response
            logger.debug(f"LLM Response: {len(content)} characters")
            logger.debug(f"Response content: {content[:200]}...")
            
            # Parse JSON if requested
            if json_mode:
                try:
                    parsed = json.loads(content)
                    return parsed
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}")
                    logger.debug(f"Raw content: {content}")
                    
                    # Try to extract JSON from markdown code blocks
                    extracted = _extract_json_from_markdown(content)
                    if extracted:
                        logger.info("Successfully extracted JSON from markdown")
                        return extracted
                    else:
                        # Try to fix common JSON issues
                        fixed = _try_fix_json(content)
                        if fixed:
                            logger.info("Successfully fixed and parsed JSON")
                            return fixed
                        else:
                            logger.error(f"Failed to parse or fix JSON. Raw content:\n{content}")
                            raise LLMError(f"Failed to parse JSON response: {e}\nRaw content: {content[:500]}...")
            else:
                return content
                
        except (APIError, APIConnectionError, RateLimitError, APITimeoutError) as e:
            last_error = e
            logger.warning(f"LLM API error (attempt {attempt + 1}/{retry_count}): {e}")
            
            # Don't retry on the last attempt
            if attempt < retry_count - 1:
                # Exponential backoff
                delay = retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"All {retry_count} retry attempts failed")
                raise LLMError(f"LLM API error after {retry_count} retries: {e}")
                
        except Exception as e:
            logger.error(f"Unexpected error in LLM call: {e}")
            raise LLMError(f"Unexpected error: {e}")
    
    # Should not reach here, but just in case
    if last_error:
        raise LLMError(f"LLM API error: {last_error}")
    else:
        raise LLMError("Unknown error in LLM call")


def _extract_json_from_markdown(content: str) -> Optional[Dict[str, Any]]:
    """
    Try to extract JSON from markdown code blocks.
    
    Handles cases where LLM wraps JSON in ```json ... ``` blocks.
    
    Args:
        content: Raw content that may contain markdown
        
    Returns:
        Parsed JSON dict if found, None otherwise
    """
    import re
    
    # Try to find JSON in code blocks
    patterns = [
        r'```json\s*\n(.*?)\n```',  # ```json ... ```
        r'```\s*\n(.*?)\n```',       # ``` ... ```
        r'`(.*?)`',                  # `...`
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match.strip())
                return parsed
            except json.JSONDecodeError:
                continue
    
    # Try to parse the entire content as JSON (in case it's valid but not in code blocks)
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass
    
    return None


def _try_fix_json(content: str) -> Optional[Dict[str, Any]]:
    """
    Try to fix common JSON issues.
    
    Args:
        content: Potentially malformed JSON string
        
    Returns:
        Parsed JSON dict if fixable, None otherwise
    """
    import re
    
    # Try to find JSON object boundaries
    # Look for outermost { ... }
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON array boundaries
    # Look for outermost [ ... ]
    match = re.search(r'\[.*\]', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    return None


def test_llm_connection():
    """
    Test LLM connection with a simple query.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        messages = [
            {
                "role": "user",
                "content": "Respond with a JSON object containing a single key 'status' with value 'ok'"
            }
        ]
        
        result = llm_call(messages, json_mode=True, max_tokens=100)
        
        if result.get("status") == "ok":
            logger.info("LLM connection test successful")
            return True
        else:
            logger.warning(f"LLM connection test returned unexpected result: {result}")
            return False
            
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test the LLM wrapper
    print("Testing LLM Wrapper:")
    print("=" * 60)
    
    # Print configuration
    print(f"LLM Base URL: {settings.LLM_BASE_URL}")
    print(f"LLM Model: {settings.LLM_MODEL}")
    print(f"LLM API Key: {'*' * 10}{settings.LLM_API_KEY[-4:]}")
    print()
    
    # Test connection
    print("Testing connection...")
    success = test_llm_connection()
    
    if success:
        print("✓ Connection successful!")
        
        # Test JSON mode
        print("\nTesting JSON mode:")
        messages = [
            {
                "role": "user",
                "content": 'Return a JSON object with keys "message" and "number" where message is "hello" and number is 42'
            }
        ]
        result = llm_call(messages, json_mode=True)
        print(f"Result: {result}")
        
    else:
        print("✗ Connection failed!")
        print("Please check your .env configuration")
    
    print("\n" + "=" * 60)
