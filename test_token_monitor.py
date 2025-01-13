import asyncio
import pytest
from dotenv import load_dotenv
import os

from src.monitor.token_monitor import TokenMonitor

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_token_monitor():
    monitor = TokenMonitor()
    
    # Test USDC token (a known token for testing)
    usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Test market cap calculation
    supply = "1000000000000"  # 1 million USDC
    decimals = 6
    price = 1.0  # USDC price should be ~$1
    
    market_cap = monitor._calculate_market_cap(supply, decimals, price)
    assert market_cap == 1000000.0, f"Expected market cap 1000000.0, got {market_cap}"
    
    # Test supply distribution analysis
    distribution_score = await monitor._analyze_supply_distribution(usdc_address)
    assert 0 <= distribution_score <= 100, f"Distribution score {distribution_score} out of range"
    
    # Test contract verification
    contract_score = await monitor._verify_contract(usdc_address)
    assert 0 <= contract_score <= 100, f"Contract score {contract_score} out of range"
    
    print("\nToken Monitor Test Results:")
    print(f"Market Cap Calculation: {'✓' if market_cap == 1000000.0 else '✗'}")
    print(f"Supply Distribution Score: {distribution_score}")
    print(f"Contract Verification Score: {contract_score}")

if __name__ == "__main__":
    asyncio.run(test_token_monitor())
