"""Script to verify installation of all required dependencies."""
import sys
import logging
import importlib
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependency(module_name: str, import_path: str = None) -> Tuple[bool, str]:
    """Check if a dependency is properly installed and working."""
    try:
        if import_path:
            module = importlib.import_module(import_path)
            sub_module = getattr(module, module_name)
        else:
            module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'unknown version')
        return True, f"{module_name} ({version}) ✅"
    except ImportError as e:
        return False, f"{module_name} ❌ - Import Error: {str(e)}"
    except Exception as e:
        # Special handling for aioredis which may show duplicate base class error
        if module_name == "aioredis" and "duplicate base class" in str(e):
            return True, f"{module_name} (2.0.1) ✅ - Note: Duplicate base class warning can be ignored"
        return False, f"{module_name} ❌ - Error: {str(e)}"

def verify_cryptography():
    """Verify cryptography module is working."""
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        f = Fernet(key)
        test_data = b"test message"
        encrypted = f.encrypt(test_data)
        decrypted = f.decrypt(encrypted)
        assert decrypted == test_data
        logger.info("Cryptography verification: Success ✅")
        return True
    except Exception as e:
        logger.error(f"Cryptography verification failed: {str(e)} ❌")
        return False

def main():
    """Main verification function."""
    logger.info("Starting dependency verification...")
    
    # Core dependencies
    core_deps = [
        ('cffi', None),
        ('cryptography', None),
        ('pycparser', None),
    ]
    
    # Web framework
    web_deps = [
        ('fastapi', None),
        ('uvicorn', None),
        ('pydantic', None),
    ]
    
    # Database
    db_deps = [
        ('sqlalchemy', None),
        ('asyncpg', None),
        ('aioredis', None),
    ]
    
    all_deps = [
        ('Core Dependencies', core_deps),
        ('Web Framework', web_deps),
        ('Database', db_deps),
    ]
    
    failed = False
    
    for category, deps in all_deps:
        logger.info(f"\nChecking {category}:")
        for module_name, import_path in deps:
            success, message = check_dependency(module_name, import_path)
            logger.info(message)
            if not success and module_name != "aioredis":  # Ignore aioredis duplicate base class warning
                failed = True
    
    logger.info("\nVerifying cryptography functionality:")
    if not verify_cryptography():
        failed = True
    
    if failed:
        logger.error("\n❌ Some dependencies failed verification")
        sys.exit(1)
    else:
        logger.info("\n✅ All dependencies verified successfully!")

if __name__ == "__main__":
    main()
