"""Mock data for testing"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Mock token data
MOCK_TOKENS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {  # USDC
        "name": "USD Coin",
        "symbol": "USDC",
        "decimals": 6,
        "supply": 1000000000,
        "price": 1.0,
        "volume_24h": 50000000,
        "holders": [
            {"address": "holder1", "balance": 1000000},
            {"address": "holder2", "balance": 500000},
            {"address": "holder3", "balance": 250000}
        ],
        "events": [
            {
                "signature": "tx1",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "type": "TRANSFER",
                "amount": 1000,
                "from_address": "holder1",
                "to_address": "holder2"
            },
            {
                "signature": "tx2",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "type": "TRANSFER",
                "amount": 500,
                "from_address": "holder2",
                "to_address": "holder3"
            }
        ],
        "deployer": {
            "address": "deployer1",
            "risk_score": 0.1,
            "verified": True
        }
    },
    "So11111111111111111111111111111111111111112": {  # Wrapped SOL
        "name": "Wrapped SOL",
        "symbol": "wSOL",
        "decimals": 9,
        "supply": 500000000,
        "price": 100.0,
        "volume_24h": 25000000,
        "holders": [
            {"address": "holder4", "balance": 2000000},
            {"address": "holder5", "balance": 1000000},
            {"address": "holder6", "balance": 500000}
        ],
        "events": [
            {
                "signature": "tx3",
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "type": "TRANSFER",
                "amount": 2000,
                "from_address": "holder4",
                "to_address": "holder5"
            }
        ],
        "deployer": {
            "address": "deployer2",
            "risk_score": 0.2,
            "verified": True
        }
    }
}

def get_mock_token(token_address: str = None) -> Dict:
    """Get mock token data"""
    if token_address is None:
        token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    token = MOCK_TOKENS.get(token_address, MOCK_TOKENS["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"])
    return {
        "address": token_address,
        "name": token["name"],
        "symbol": token["symbol"],
        "decimals": token["decimals"],
        "supply": token["supply"],
        "price": token["price"],
        "volume_24h": token["volume_24h"],
        "holder_concentration": 0.5,  # Mock value
        "price_volatility": 0.2,  # Mock value
        "volume_change": 0.1  # Mock value
    }

def get_mock_holders(token_address: str = None) -> List[Dict]:
    """Get mock holders for a token"""
    if token_address is None:
        token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    token = MOCK_TOKENS.get(token_address, MOCK_TOKENS["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"])
    return token["holders"]

def get_mock_transactions(token_address: str = None) -> List[Dict]:
    """Get mock transactions for a token"""
    if token_address is None:
        token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    token = MOCK_TOKENS.get(token_address, MOCK_TOKENS["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"])
    return token["events"]

def get_mock_deployer(token_address: str = None) -> Dict:
    """Get mock deployer data for a token"""
    if token_address is None:
        token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    token = MOCK_TOKENS.get(token_address, MOCK_TOKENS["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"])
    return token["deployer"]

def get_mock_price(token_address: str = None) -> float:
    """Get mock price for a token"""
    if token_address is None:
        token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    token = MOCK_TOKENS.get(token_address, MOCK_TOKENS["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"])
    return token["price"]

def get_mock_volume(token_address: str = None) -> float:
    """Get mock volume for a token"""
    if token_address is None:
        token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    token = MOCK_TOKENS.get(token_address, MOCK_TOKENS["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"])
    return token["volume_24h"]

def should_use_mock_data() -> bool:
    """Check if mock data should be used"""
    return True
