import re
import base58
from typing import Optional, Tuple

def validate_solana_address(address: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a Solana address (public key) in base58 format.
    Returns (is_valid, error_message).
    """
    if not address:
        return False, "Empty address"
        
    try:
        # Check length of the base58 string (should be 32-44 chars)
        if len(address) < 32 or len(address) > 44:
            return False, f"Invalid address length: {len(address)}"
            
        # Check base58 character set
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]+$', address):
            return False, "Invalid characters in address"
            
        # Try to decode base58
        try:
            decoded = base58.b58decode(address)
            # Solana addresses are 32 bytes
            if len(decoded) != 32:
                return False, f"Decoded length is not 32 bytes: {len(decoded)}"
        except Exception as e:
            return False, f"Invalid base58 encoding: {str(e)}"
            
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def encode_solana_address(public_key_bytes: bytes) -> str:
    """
    Encode a 32-byte public key as a base58 Solana address.
    """
    if len(public_key_bytes) != 32:
        raise ValueError(f"Public key must be 32 bytes, got {len(public_key_bytes)}")
    return base58.b58encode(public_key_bytes).decode('ascii')

def decode_solana_address(address: str) -> bytes:
    """
    Decode a base58 Solana address into its 32-byte public key.
    """
    is_valid, error = validate_solana_address(address)
    if not is_valid:
        raise ValueError(f"Invalid Solana address: {error}")
    return base58.b58decode(address)

def is_program_address(address: str) -> bool:
    """
    Check if an address is likely a program address.
    Program addresses often start with specific patterns.
    """
    program_prefixes = [
        '1111111',  # System Program
        'So111111', # Wrapped SOL
        'Token',    # Token Program
        'AToken',   # Associated Token Program
        'Meta',     # Metadata Program
        'Stake',    # Stake Program
        'Vote',     # Vote Program
    ]
    return any(address.startswith(prefix) for prefix in program_prefixes)

def get_address_type(address: str) -> str:
    """
    Get the likely type of a Solana address.
    """
    is_valid, error = validate_solana_address(address)
    if not is_valid:
        return "invalid"
        
    if is_program_address(address):
        return "program"
        
    # Check if it's a token mint (usually has specific patterns)
    if address.startswith(('So1', 'EPj', 'SRM', 'RAY')):
        return "token"
        
    return "wallet"  # Default to wallet address
