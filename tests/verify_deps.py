"""Verify that all required dependencies are installed correctly."""
import sys
import importlib

def test_cryptography():
    """Test that cryptography is installed and working."""
    try:
        import cryptography
        from cryptography.fernet import Fernet
        # Try to use it
        key = Fernet.generate_key()
        f = Fernet(key)
        print("✅ Cryptography installed and working")
    except ImportError as e:
        print(f"❌ Failed to import cryptography: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Cryptography test failed: {e}")
        sys.exit(1)

def test_dependencies():
    """Test that all critical dependencies are installed."""
    dependencies = [
        'fastapi',
        'uvicorn',
        'cryptography',
        'cffi',
        'python-jose',
        'passlib',
        'sqlalchemy',
        'aiohttp'
    ]
    
    for dep in dependencies:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep} installed")
        except ImportError as e:
            print(f"❌ Failed to import {dep}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    print("Running dependency verification...")
    test_cryptography()
    test_dependencies()
    print("All dependencies verified successfully!")
