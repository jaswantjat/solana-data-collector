"""Test script to verify all dependencies are working correctly."""
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_core_dependencies():
    """Test core dependencies."""
    try:
        import cffi
        logger.info(f"✅ cffi {cffi.__version__} installed successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import cffi: {e}")
        sys.exit(1)

    try:
        import cryptography
        from cryptography.fernet import Fernet
        # Test Fernet functionality
        key = Fernet.generate_key()
        f = Fernet(key)
        test_data = b"test message"
        encrypted = f.encrypt(test_data)
        decrypted = f.decrypt(encrypted)
        assert decrypted == test_data
        logger.info(f"✅ cryptography {cryptography.__version__} installed and working")
    except ImportError as e:
        logger.error(f"❌ Failed to import cryptography: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Cryptography test failed: {e}")
        sys.exit(1)

def test_web_dependencies():
    """Test web framework dependencies."""
    try:
        import fastapi
        import uvicorn
        import pydantic
        logger.info(f"✅ FastAPI {fastapi.__version__} installed successfully")
        logger.info(f"✅ Uvicorn {uvicorn.__version__} installed successfully")
        logger.info(f"✅ Pydantic {pydantic.__version__} installed successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import web dependencies: {e}")
        sys.exit(1)

def main():
    """Run all tests."""
    logger.info("Starting dependency verification...")
    
    test_core_dependencies()
    test_web_dependencies()
    
    logger.info("All dependencies verified successfully! ✨")

if __name__ == "__main__":
    main()
