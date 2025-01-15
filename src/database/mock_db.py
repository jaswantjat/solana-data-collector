"""Mock database module for testing and development."""
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class MockQueryResult:
    def __init__(self, result: Any):
        self._result = result

    def scalar(self) -> Any:
        """Return a single value from the result."""
        if isinstance(self._result, (list, tuple)) and len(self._result) > 0:
            return self._result[0]
        return self._result

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """Return a single row from the result."""
        if isinstance(self._result, (list, tuple)) and len(self._result) > 0:
            return self._result[0]
        return None

    def fetchall(self) -> List[Dict[str, Any]]:
        """Return all rows from the result."""
        if isinstance(self._result, (list, tuple)):
            return self._result
        return [self._result] if self._result is not None else []

class MockDatabase:
    """Mock database for testing and development."""
    
    def __init__(self):
        """Initialize mock database."""
        self.tokens = {}
        self.wallets = {}
        self.transactions = {}
        self.blacklist = {}
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass
    
    def execute(self, query: str, params: Tuple = None) -> MockQueryResult:
        """Execute a mock query."""
        if "SELECT 1" in query:
            return MockQueryResult(1)
        elif "SELECT COUNT(*)" in query:
            return MockQueryResult(0)
        elif "SELECT * FROM tokens" in query:
            if params and params[0] in self.tokens:
                return MockQueryResult([self.tokens[params[0]]])
            return MockQueryResult([])
        elif "SELECT * FROM transactions" in query:
            return MockQueryResult(list(self.transactions.values()))
        return MockQueryResult([])
    
    def add_token(self, token_address: str, token_data: Dict) -> None:
        """Add a token to the mock database."""
        self.tokens[token_address] = {
            **token_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    def get_token(self, token_address: str) -> Optional[Dict]:
        """Get a token from the mock database."""
        return self.tokens.get(token_address)
    
    def add_wallet(self, wallet_address: str, wallet_data: Dict) -> None:
        """Add a wallet to the mock database."""
        self.wallets[wallet_address] = {
            **wallet_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    def get_wallet(self, wallet_address: str) -> Optional[Dict]:
        """Get a wallet from the mock database."""
        return self.wallets.get(wallet_address)
    
    def add_transaction(self, tx_hash: str, tx_data: Dict) -> None:
        """Add a transaction to the mock database."""
        self.transactions[tx_hash] = {
            **tx_data,
            "created_at": datetime.utcnow()
        }
    
    def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get a transaction from the mock database."""
        return self.transactions.get(tx_hash)
    
    def add_to_blacklist(self, address: str, reason: str) -> None:
        """Add an address to the blacklist."""
        self.blacklist[address] = {
            "reason": reason,
            "created_at": datetime.utcnow()
        }
    
    def is_blacklisted(self, address: str) -> bool:
        """Check if an address is blacklisted."""
        return address in self.blacklist
    
    def get_blacklist_stats(self) -> Dict:
        """Get statistics about blacklisted addresses."""
        return {
            "total_blacklisted": len(self.blacklist),
            "total_scam_amount": 0.0,  # Mock value
            "recent_additions": [
                {"address": addr, **data}
                for addr, data in list(self.blacklist.items())[-10:]
            ]
        }
    
    def get_recent_transactions(self, limit: int = 100) -> List[Dict]:
        """Get recent transactions."""
        return list(self.transactions.values())[-limit:]
    
    def get_token_transactions(self, token_address: str, limit: int = 100) -> List[Dict]:
        """Get transactions for a specific token."""
        return [
            tx for tx in self.transactions.values()
            if tx.get("token_address") == token_address
        ][-limit:]
    
    def get_wallet_transactions(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Get transactions for a specific wallet."""
        return [
            tx for tx in self.transactions.values()
            if tx.get("from_address") == wallet_address or tx.get("to_address") == wallet_address
        ][-limit:]

# Create a global instance of MockDatabase
mock_db = MockDatabase()
