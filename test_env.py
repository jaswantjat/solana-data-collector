import sys
import os
import pkg_resources

def test_cryptography():
    try:
        import cryptography
        print(f"✅ cryptography {cryptography.__version__}")
        
        # Test Fernet functionality
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        f = Fernet(key)
        test_data = b"test message"
        token = f.encrypt(test_data)
        decrypted = f.decrypt(token)
        assert decrypted == test_data
        print("✅ Fernet encryption/decryption working")
        
    except ImportError as e:
        print(f"❌ cryptography import failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ cryptography test failed: {e}")
        sys.exit(1)

def test_dependencies():
    required = {
        'cryptography': '41.0.7',
        'cffi': '1.15.1',
        'pycparser': '2.21'
    }
    
    for package, version in required.items():
        try:
            dist = pkg_resources.get_distribution(package)
            print(f"✅ {package} {dist.version} (required: {version})")
            if dist.version != version:
                print(f"⚠️  Warning: {package} version mismatch")
        except pkg_resources.DistributionNotFound:
            print(f"❌ {package} not found")
            sys.exit(1)

def main():
    print("\n=== Python Environment Information ===")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print(f"Virtual Env: {os.environ.get('VIRTUAL_ENV', 'Not set')}")
    
    print("\n=== Testing Dependencies ===")
    test_dependencies()
    
    print("\n=== Testing Cryptography ===")
    test_cryptography()
    
    print("\n=== Python Path ===")
    for path in sys.path:
        print(f"  - {path}")
    
    print("\n✅ All tests passed successfully!")

if __name__ == "__main__":
    main()
