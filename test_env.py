import sys
import os

def main():
    print("Python Environment Information:")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print(f"Virtual Env: {os.environ.get('VIRTUAL_ENV', 'Not set')}")
    print("\nTesting imports:")
    
    try:
        import cryptography
        print(f"✅ cryptography {cryptography.__version__}")
    except ImportError as e:
        print(f"❌ cryptography: {e}")
    
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        f = Fernet(key)
        print("✅ Fernet working")
    except ImportError as e:
        print(f"❌ Fernet: {e}")
    
    print("\nPython Path:")
    for path in sys.path:
        print(f"  - {path}")

if __name__ == "__main__":
    main()
