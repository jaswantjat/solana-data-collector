import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

# Set environment variables for testing
os.environ["HELIUS_API_KEY"] = "5666d667-4bd6-4d71-bce4-f84791b707d0"
os.environ["BIRDEYE_API_KEY"] = "test_birdeye_key"
os.environ["JUPITER_API_KEY"] = "test_jupiter_key"
os.environ["COINGECKO_API_KEY"] = "test_coingecko_key"
os.environ["SHYFT_API_KEY"] = "test_shyft_key"
os.environ["BITQUERY_API_KEY"] = "test_bitquery_key"

from src.analysis.market_analysis import MarketAnalysis
from src.analysis.holder_analysis import HolderAnalysis
from src.analysis.deployer_analysis import DeployerAnalysis
from src.analysis.transaction_analysis import TransactionAnalysis
from src.error_handling.error_manager import ErrorManager
from src.integrations.api_manager import APIManager
from src.utils.solana_utils import validate_solana_address

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalysisPipelineTest:
    def __init__(self):
        # Initialize components
        self.api_manager = APIManager()
        self.market_analysis = MarketAnalysis()
        self.holder_analysis = HolderAnalysis()
        self.deployer_analysis = DeployerAnalysis()
        self.transaction_analysis = TransactionAnalysis()
        
        # Test tokens (mix of real and invalid tokens)
        self.test_tokens = {
            "valid": [
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                "So11111111111111111111111111111111111111112",   # Wrapped SOL
                "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
            ],
            "invalid": [
                "InvalidToken123456789",
                "NotARealToken987654321",
                "0x1234567890"  # Ethereum format
            ],
            "edge_cases": [
                "",  # Empty string
                "0" * 44,  # All zeros
                "1" * 44,  # All ones
                "!@#$%^&*()"  # Invalid characters
            ]
        }
        
        # Expected value ranges
        self.valid_ranges = {
            "market_cap": (0, 1e12),  # 0 to 1 trillion
            "holder_count": (0, 1e7),  # 0 to 10 million
            "price": (0, 1e6),        # 0 to 1 million
            "volume": (0, 1e12),      # 0 to 1 trillion
            "risk_score": (0, 100)    # 0 to 100
        }
        
        self.total_tests = 0
        self.successful_tests = 0
        self.failed_tests = 0
        self.alerts_triggered = 0

    async def initialize(self):
        """Initialize all components"""
        await self.market_analysis.initialize()
        await self.holder_analysis.initialize()
        await self.deployer_analysis.initialize()
        await self.transaction_analysis.initialize()

    async def close(self):
        """Close all API sessions"""
        try:
            await self.market_analysis.close()
            await self.holder_analysis.close()
            await self.deployer_analysis.close()
            await self.transaction_analysis.close()
        except Exception as e:
            logger.error(f"Error closing sessions: {str(e)}")

    def validate_input(self, token_address: str) -> bool:
        """Validate token address format"""
        is_valid, error = validate_solana_address(token_address)
        if not is_valid:
            logger.error(error)
            return False
        return True

    def validate_output_format(self, data: Dict) -> bool:
        """Validate analysis output format"""
        required_fields = {
            "market_data": ["market_cap", "price", "volume_24h"],
            "holder_data": ["total_holders", "whale_concentration", "distribution"],
            "deployer_data": ["deployer_address", "risk_score", "analysis"],
            "transaction_data": ["transaction_count", "buy_sell_ratio", "avg_transaction_size"]
        }
        
        for category, fields in required_fields.items():
            if category not in data:
                logger.error(f"Missing category: {category}")
                return False
            for field in fields:
                if field not in data[category]:
                    logger.error(f"Missing field: {field} in {category}")
                    return False
                    
        return True

    def validate_calculation_ranges(self, data: Dict) -> bool:
        """Validate if calculated values are within expected ranges"""
        try:
            # Market data validation
            market_cap = float(data["market_data"]["market_cap"])
            if not self.valid_ranges["market_cap"][0] <= market_cap <= self.valid_ranges["market_cap"][1]:
                logger.warning(f"Market cap out of range: {market_cap}")
                
            # Holder data validation
            holder_count = int(data["holder_data"]["total_holders"])
            if not self.valid_ranges["holder_count"][0] <= holder_count <= self.valid_ranges["holder_count"][1]:
                logger.warning(f"Holder count out of range: {holder_count}")
                
            # Risk score validation
            risk_score = float(data["deployer_data"]["risk_score"])
            if not self.valid_ranges["risk_score"][0] <= risk_score <= self.valid_ranges["risk_score"][1]:
                logger.warning(f"Risk score out of range: {risk_score}")
                
            return True
            
        except (ValueError, KeyError) as e:
            logger.error(f"Validation error: {str(e)}")
            return False

    def check_alert_conditions(self, data: Dict) -> List[str]:
        """Check if any alert conditions are met"""
        alerts = []
        
        # Market cap alerts
        if data["market_data"]["market_cap"] > 1e9:  # > $1B
            alerts.append("HIGH_MARKET_CAP")
        elif data["market_data"]["market_cap"] < 1e3:  # < $1K
            alerts.append("LOW_MARKET_CAP")
            
        # Holder concentration alerts
        if data["holder_data"]["whale_concentration"] > 80:  # >80% whale concentration
            alerts.append("HIGH_WHALE_CONCENTRATION")
            
        # Risk score alerts
        if data["deployer_data"]["risk_score"] > 80:  # High risk
            alerts.append("HIGH_RISK_SCORE")
            
        # Transaction alerts
        if data["transaction_data"]["buy_sell_ratio"] > 3:  # Buy/sell ratio > 3
            alerts.append("HIGH_BUY_PRESSURE")
        elif data["transaction_data"]["buy_sell_ratio"] < 0.33:  # Buy/sell ratio < 1/3
            alerts.append("HIGH_SELL_PRESSURE")
            
        return alerts

    async def analyze_token(self, token_address: str) -> Dict:
        """Run complete analysis pipeline for a token"""
        try:
            # Step 1: Input validation
            if not self.validate_input(token_address):
                raise ValueError(f"Invalid token address: {token_address}")
                
            # Step 2: Gather all data
            market_data = await self.market_analysis.analyze_market(token_address)
            holder_data = await self.holder_analysis.analyze_holders(token_address)
            deployer_data = await self.deployer_analysis.analyze_deployer(token_address)
            transaction_data = await self.transaction_analysis.analyze_transactions(token_address)
            
            # Step 3: Combine results
            analysis_result = {
                "token_address": token_address,
                "timestamp": datetime.now().isoformat(),
                "market_data": market_data,
                "holder_data": holder_data,
                "deployer_data": deployer_data,
                "transaction_data": transaction_data
            }
            
            # Step 4: Validate output format
            if not self.validate_output_format(analysis_result):
                raise ValueError("Invalid output format")
                
            # Step 5: Validate calculations
            if not self.validate_calculation_ranges(analysis_result):
                logger.warning("Some calculations outside expected ranges")
                
            # Step 6: Check for alerts
            alerts = self.check_alert_conditions(analysis_result)
            analysis_result["alerts"] = alerts
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Analysis pipeline failed for {token_address}: {str(e)}")
            raise

    async def _test_valid_tokens(self):
        """Test valid tokens"""
        for token in self.test_tokens["valid"]:
            try:
                result = await self.analyze_token(token)
                self.successful_tests += 1
                self.alerts_triggered += len(result["alerts"])
            except Exception as e:
                logger.error(f"Test failed for {token}: {str(e)}")
                self.failed_tests += 1
            self.total_tests += 1

    async def _test_invalid_tokens(self):
        """Test invalid tokens"""
        for token in self.test_tokens["invalid"]:
            try:
                result = await self.analyze_token(token)
                logger.error(f"Unexpected success for {token}")
                self.failed_tests += 1
            except Exception as e:
                self.successful_tests += 1
            self.total_tests += 1

    async def _test_edge_cases(self):
        """Test edge cases"""
        for token in self.test_tokens["edge_cases"]:
            try:
                result = await self.analyze_token(token)
                logger.error(f"Unexpected success for {token}")
                self.failed_tests += 1
            except Exception as e:
                self.successful_tests += 1
            self.total_tests += 1

    async def run_tests(self):
        """Run all tests"""
        try:
            await self.initialize()
            
            # Test valid tokens
            logger.info("\n🧪 Testing valid tokens...")
            await self._test_valid_tokens()
            
            # Test invalid tokens
            logger.info("\n🧪 Testing invalid tokens...")
            await self._test_invalid_tokens()
            
            # Test edge cases
            logger.info("\n🧪 Testing edge cases...")
            await self._test_edge_cases()
            
            # Print summary
            logger.info("\n📊 Test Summary:")
            logger.info(f"Total Tests: {self.total_tests}")
            logger.info(f"Successful: {self.successful_tests}")
            logger.info(f"Failed: {self.failed_tests}")
            logger.info(f"Success Rate: {(self.successful_tests/self.total_tests)*100:.1f}%")
            logger.info(f"Alerts Triggered: {self.alerts_triggered}")
            
        finally:
            await self.close()
            await asyncio.sleep(0.1)  # Give time for sessions to close
            
async def main():
    test_suite = AnalysisPipelineTest()
    try:
        await test_suite.initialize()
        await test_suite.run_tests()
    finally:
        await test_suite.close()
        await asyncio.sleep(0.2)  # Give more time for sessions to close
    
if __name__ == "__main__":
    asyncio.run(main())
