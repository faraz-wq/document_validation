"""
Test script for LLM wrapper configuration and connection.

This script helps you:
1. Check if LLM credentials are configured
2. Test the LLM connection
3. Verify JSON mode works correctly
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = Path(__file__).parent.parent / ".env"
    
    print("=" * 70)
    print("LLM Wrapper Configuration Test")
    print("=" * 70)
    print()
    
    if not env_path.exists():
        print("❌ .env file not found!")
        print(f"   Expected location: {env_path}")
        print()
        print("Please create a .env file with the following content:")
        print()
        print("   LLM_BASE_URL=https://api.openai.com/v1")
        print("   LLM_MODEL=gpt-4o")
        print("   LLM_API_KEY=your-api-key-here")
        print()
        return False
    
    print(f"✓ .env file found at: {env_path}")
    print()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    # Check required variables
    llm_base_url = os.getenv("LLM_BASE_URL")
    llm_model = os.getenv("LLM_MODEL")
    llm_api_key = os.getenv("LLM_API_KEY")
    
    print("Configuration:")
    print(f"  LLM_BASE_URL: {llm_base_url or '❌ NOT SET'}")
    print(f"  LLM_MODEL: {llm_model or '❌ NOT SET'}")
    print(f"  LLM_API_KEY: {'✓ SET' if llm_api_key else '❌ NOT SET'}")
    print()
    
    if not llm_api_key:
        print("❌ LLM_API_KEY is not set!")
        print()
        print("Please add the following to your .env file:")
        print()
        print("   LLM_API_KEY=your-api-key-here")
        print()
        print("Supported providers:")
        print("  - OpenAI: https://api.openai.com/v1")
        print("  - Azure OpenAI: https://your-resource.openai.azure.com/...")
        print("  - Together AI: https://api.together.xyz/v1")
        print("  - OpenRouter: https://openrouter.ai/api/v1")
        print("  - Ollama (local): http://localhost:11434/v1")
        print("  - LM Studio (local): http://localhost:1234/v1")
        print()
        return False
    
    return True


def test_llm_connection():
    """Test LLM connection."""
    try:
        from core.llm_wrapper import llm_call, test_llm_connection
        
        print("Testing LLM connection...")
        print()
        
        success = test_llm_connection()
        
        if success:
            print("✓ LLM connection successful!")
            print()
            
            # Test JSON mode
            print("Testing JSON mode...")
            messages = [
                {
                    "role": "user",
                    "content": 'Return a JSON object with keys "greeting" and "number" where greeting is "hello" and number is 42'
                }
            ]
            result = llm_call(messages, json_mode=True, max_tokens=100)
            print(f"  Result: {result}")
            
            if isinstance(result, dict) and "greeting" in result:
                print("✓ JSON mode working correctly!")
                return True
            else:
                print("❌ JSON mode returned unexpected result")
                return False
        else:
            print("❌ LLM connection failed!")
            print()
            print("Possible issues:")
            print("  - Invalid API key")
            print("  - Incorrect base URL")
            print("  - Network connectivity issues")
            print("  - Model not available")
            return False
            
    except Exception as e:
        print(f"❌ Error testing LLM connection: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    # Check environment configuration
    if not check_env_file():
        print("=" * 70)
        print("Please configure your .env file and run this script again.")
        print("=" * 70)
        sys.exit(1)
    
    # Test LLM connection
    print("=" * 70)
    success = test_llm_connection()
    print("=" * 70)
    
    if success:
        print()
        print("🎉 All tests passed! LLM wrapper is ready to use.")
        print()
        sys.exit(0)
    else:
        print()
        print("⚠️  LLM connection test failed. Please check your configuration.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
