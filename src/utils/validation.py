"""Validation utilities"""
import re
import os

def validate_solana_address(address: str) -> bool:
    """Validate a Solana address"""
    if not address:
        return False
        
    # Skip validation in test mode
    if os.getenv("TEST_MODE", "false").lower() == "true":
        return True
        
    # Check length (base58 encoded public key)
    if len(address) != 44:
        return False
        
    # Check characters (base58 alphabet)
    if not re.match(r'^[1-9A-HJ-NP-Za-km-z]+$', address):
        return False
        
    return True
