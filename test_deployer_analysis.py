import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from src.analysis.deployer_analysis import DeployerAnalysis

class MockHeliusAPI:
    async def get_token_deployer(self, address):
        return "test_deployer"

    async def get_deployer_tokens(self, address):
        if address == "test_deployer_address":
            return [
                {"address": "token1", "success": True},
                {"address": "token2", "success": True},
                {"address": "token3", "success": False}
            ]
        elif address == "high_risk_deployer":
            return [
                {"address": "failed1", "success": False},
                {"address": "failed2", "success": False},
                {"address": "failed3", "success": False},
                {"address": "failed4", "success": False},
                {"address": "failed5", "success": False}
            ]
        return []

    async def get_token_metadata(self, address):
        return {
            "onChainMetadata": {
                "metadata": {
                    "updateAuthority": {
                        "createdAt": datetime.now().isoformat()
                    }
                }
            }
        }

    async def get_token_supply(self, address):
        if address.startswith("token"):
            return {
                "supply": "1000000000",
                "decimals": 9
            }
        else:
            return {
                "supply": "100000000",
                "decimals": 9
            }

class MockJupiterAPI:
    async def get_token_price(self, address):
        if address == "token1":
            return {"price": 0.005}  # High MC (5M with 1B supply)
        elif address == "token2":
            return {"price": 0.003}  # Medium MC (3M with 1B supply)
        elif address == "token3":
            return {"price": 0.0001}  # Low MC (100k with 1B supply)
        elif address.startswith("failed"):
            return {"price": 0.000001}  # Very low MC (100 with 100M supply)
        return {"price": 0.0}

@pytest.fixture
def deployer_analysis():
    with patch('src.analysis.deployer_analysis.HeliusAPI', return_value=MockHeliusAPI()), \
         patch('src.analysis.deployer_analysis.JupiterAPI', return_value=MockJupiterAPI()):
        analysis = DeployerAnalysis()
        # Clear any existing data
        analysis.blacklist = {"deployers": [], "tokens": []}
        analysis.deployer_history = {}
        return analysis

@pytest.mark.asyncio
async def test_new_deployer_profile(deployer_analysis):
    """Test creating a new deployer profile"""
    profile = deployer_analysis._create_new_deployer_profile("test_address")
    assert profile["address"] == "test_address"
    assert profile["risk_level"] == "Medium"
    assert profile["success_rate"] == 0
    assert not profile["blacklisted"]

@pytest.mark.asyncio
async def test_blacklist_functionality(deployer_analysis):
    """Test blacklist functionality"""
    # Add to blacklist
    deployer_analysis.blacklist["deployers"].append("blacklisted_address")
    deployer_analysis._save_blacklist()
    
    # Check if blacklisted
    assert deployer_analysis.is_blacklisted("blacklisted_address")
    assert not deployer_analysis.is_blacklisted("clean_address")

@pytest.mark.asyncio
async def test_deployer_analysis(deployer_analysis):
    """Test deployer analysis functionality"""
    analysis = await deployer_analysis.analyze_deployer("test_deployer_address")
    
    # Verify analysis structure
    assert analysis["address"] == "test_deployer_address"
    assert "risk_level" in analysis
    assert "success_rate" in analysis
    assert analysis["total_tokens"] == 3
    assert analysis["successful_tokens"] == 2  # token1 and token2 > 3M MC
    assert analysis["failed_tokens"] == 1  # token3 < 200k MC
    assert "avg_token_age" in analysis
    assert "total_mc" in analysis
    assert isinstance(analysis["history"], list)
    assert len(analysis["history"]) == 3

@pytest.mark.asyncio
async def test_high_risk_blacklisting(deployer_analysis):
    """Test automatic blacklisting of high-risk deployers"""
    # First analysis should detect high risk and blacklist
    analysis = await deployer_analysis.analyze_deployer("high_risk_deployer")
    
    # Should be high risk and blacklisted
    assert analysis["risk_level"] == "High"
    assert analysis["total_tokens"] == 5
    assert analysis["failed_tokens"] == 5
    assert analysis["successful_tokens"] == 0
    assert deployer_analysis.is_blacklisted("high_risk_deployer")

    # Second analysis should return blacklisted profile
    analysis2 = await deployer_analysis.analyze_deployer("high_risk_deployer")
    assert analysis2["blacklisted"]
    assert analysis2["risk_level"] == "High"
    assert analysis2["total_tokens"] == 0  # Blacklisted profile has no tokens

if __name__ == "__main__":
    pytest.main([__file__])
