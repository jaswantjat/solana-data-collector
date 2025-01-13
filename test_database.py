import pytest
from datetime import datetime, timedelta
from src.database.db_manager import DatabaseManager

@pytest.fixture
def db_manager():
    return DatabaseManager()

def test_wallet_database(db_manager):
    """Test wallet database operations"""
    # Test scammer wallet
    assert db_manager.add_scammer_wallet(
        "scammer_address",
        {"type": "rug_pull", "tokens_stolen": 1000}
    )
    
    # Test trusted trader
    assert db_manager.add_trusted_trader(
        "trader_address",
        {
            "success_rate": 0.8,
            "age_days": 180,
            "volume": 500000
        }
    )
    
    # Test sniper wallet
    assert db_manager.add_sniper_wallet(
        "sniper_address",
        {
            "pattern": "quick_buy_sell",
            "confidence": 0.9
        }
    )
    
    # Test insider wallet
    assert db_manager.add_insider_wallet(
        "insider_address",
        {
            "pattern": "pre_pump_buy",
            "confidence": 0.85
        }
    )
    
    # Test performance metrics
    assert db_manager.update_wallet_performance(
        "wallet_address",
        {
            "win_rate": 0.7,
            "total_trades": 100,
            "avg_profit": 0.15
        }
    )
    
    # Verify wallet status
    status = db_manager.get_wallet_status("scammer_address")
    assert status["is_scammer"]
    assert status["blacklist_status"]["scammer"]

def test_token_database(db_manager):
    """Test token database operations"""
    # Test token addition
    assert db_manager.add_token(
        "token_address",
        {
            "name": "Test Token",
            "symbol": "TEST",
            "decimals": 9
        }
    )
    
    # Test launch data
    assert db_manager.add_token_launch(
        "token_address",
        {
            "initial_price": 0.0001,
            "initial_liquidity": 10000,
            "launch_time": datetime.now().isoformat()
        }
    )
    
    # Test performance metrics
    assert db_manager.update_token_performance(
        "token_address",
        {
            "price_change": 0.5,
            "volume": 100000,
            "holders": 1000
        }
    )
    
    # Test risk score
    assert db_manager.update_token_risk_score(
        "token_address",
        {
            "score": 0.3,
            "factors": {
                "liquidity": 0.4,
                "holder_concentration": 0.2
            }
        }
    )
    
    # Test price data
    assert db_manager.add_price_data(
        "token_address",
        {
            "price": 0.0002,
            "timestamp": datetime.now().isoformat(),
            "volume": 50000
        }
    )

def test_blacklist_database(db_manager):
    """Test blacklist database operations"""
    # Test scammer address
    assert db_manager.add_to_blacklist(
        "scammer_addresses",
        "scammer_address",
        {"reason": "rug_pull", "evidence": "transaction_hash"}
    )
    
    # Test failed deployer
    assert db_manager.add_to_blacklist(
        "failed_deployers",
        "deployer_address",
        {"failed_projects": 3, "total_loss": 50000}
    )
    
    # Test suspicious pattern
    assert db_manager.add_suspicious_pattern(
        {
            "type": "wash_trading",
            "description": "Circular trading between related wallets",
            "severity": "high"
        }
    )
    
    # Test compromised contract
    assert db_manager.add_compromised_contract(
        "contract_address",
        {
            "vulnerability": "honeypot",
            "detection_time": datetime.now().isoformat()
        }
    )
