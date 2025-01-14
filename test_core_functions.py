import asyncio
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
from src.integrations.helius import HeliusAPI
from src.integrations.shyft import ShyftAPI
from src.integrations.bitquery import BitqueryAPI
from src.analysis.holder_analysis import HolderAnalysis
from src.analysis.deployer_analysis import DeployerAnalysis
from src.analysis.market_analysis import MarketAnalysis
from src.monitoring.token_monitor import TokenMonitor
from src.monitoring.transaction_monitor import TransactionMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class CoreFunctionTester:
    def __init__(self):
        # Initialize APIs
        self.helius = HeliusAPI()
        self.shyft = ShyftAPI()
        self.bitquery = BitqueryAPI()
        
        # Initialize analysis modules
        self.holder_analysis = HolderAnalysis()
        self.deployer_analysis = DeployerAnalysis()
        self.market_analysis = MarketAnalysis()
        
        # Initialize monitors
        self.token_monitor = TokenMonitor()
        self.transaction_monitor = TransactionMonitor()
        
        # Test tokens (known successful and failed launches)
        self.test_tokens = {
            'successful': [
                'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  # BONK
                '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'   # SAMO
            ],
            'failed': [
                '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R',  # Random failed token
                '2FPyTwcZLUg1MDrwsyoP4D6s1tM7hAkHYRjkNb5w6Pxk'   # Another failed token
            ]
        }
    
    async def __aenter__(self):
        """Initialize test environment"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment"""
        await self.cleanup()
        
    async def initialize(self):
        """Initialize API connections"""
        await self.helius.initialize()
        await self.market_analysis.initialize()
        # Add other initializations if needed
        
    async def cleanup(self):
        """Cleanup API connections"""
        await self.helius.close()
        await self.market_analysis.close()
        # Add other cleanup if needed

    async def test_token_launch_detection(self):
        """Test token launch detection functionality"""
        logger.info("\n🔍 Testing Token Launch Detection...")
        try:
            # Test with recent timeframe
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            new_tokens = await self.token_monitor.detect_new_launches(
                start_time=start_time,
                end_time=end_time
            )
            
            logger.info(f"✅ Detected {len(new_tokens)} new token launches in the last 24 hours")
            for token in new_tokens[:5]:  # Show first 5 tokens
                logger.info(f"Token: {token['mint']}, Launch Time: {token['launch_time']}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Token Launch Detection Failed: {str(e)}")
            return False

    async def test_market_cap_tracking(self):
        """Test market cap tracking functionality"""
        logger.info("\n📊 Testing Market Cap Tracking...")
        try:
            for token_type, tokens in self.test_tokens.items():
                logger.info(f"\nTesting {token_type} tokens:")
                for token in tokens:
                    market_data = await self.market_analysis.get_market_data(token)
                    logger.info(f"Token: {token}")
                    logger.info(f"Market Cap: ${market_data['market_cap']:,.2f}")
                    logger.info(f"Price: ${market_data['price']:,.8f}")
                    logger.info(f"24h Volume: ${market_data['volume_24h']:,.2f}")
            return True
        except Exception as e:
            logger.error(f"❌ Market Cap Tracking Failed: {str(e)}")
            return False

    async def test_deployer_analysis(self):
        """Test deployer analysis functionality"""
        logger.info("\n👨‍💻 Testing Deployer Analysis...")
        try:
            for token_type, tokens in self.test_tokens.items():
                logger.info(f"\nAnalyzing {token_type} token deployers:")
                for token in tokens:
                    logger.info(f"Token: {token}")
                    try:
                        deployer_data = await self.deployer_analysis.analyze_deployer(token)
                        
                        if deployer_data["deployer_address"]:
                            logger.info(f"Deployer: {deployer_data['deployer_address']}")
                            logger.info(f"Risk Score: {deployer_data['risk_score']}/100")
                            logger.info("Analysis:")
                            logger.info(f"- Token Count: {deployer_data['analysis']['token_count']}")
                            logger.info(f"- Success Rate: {deployer_data['analysis']['success_rate']:.2%}")
                            logger.info(f"- Average Token Age: {deployer_data['analysis']['avg_token_age']:.1f} days")
                            logger.info(f"- Verified: {'Yes' if deployer_data['analysis']['verified'] else 'No'}")
                        else:
                            logger.info("No deployer information found")
                            
                    except Exception as e:
                        logger.error(f"❌ Deployer Analysis Failed: {str(e)}")
            return True
        except Exception as e:
            logger.error(f"❌ Deployer Analysis Failed: {str(e)}")
            return False

    async def test_holder_analysis(self):
        """Test holder analysis functionality"""
        logger.info("\n👥 Testing Holder Analysis...")
        try:
            for token_type, tokens in self.test_tokens.items():
                logger.info(f"\nAnalyzing {token_type} token holders:")
                for token in tokens:
                    holder_data = await self.holder_analysis.analyze_holders(token)
                    logger.info(f"Token: {token}")
                    logger.info(f"Total Holders: {holder_data['total_holders']}")
                    logger.info(f"Whale Concentration: {holder_data['whale_concentration']:.2f}%")
                    
                    # Print distribution summary
                    dist = holder_data["distribution"]
                    logger.info("Distribution Summary:")
                    logger.info(f"- Whales (>1%): {dist['whales']:.2f}%")
                    logger.info(f"- Large Holders (0.1-1%): {dist['large_holders']:.2f}%")
                    logger.info(f"- Medium Holders (0.01-0.1%): {dist['medium_holders']:.2f}%")
                    logger.info(f"- Small Holders (<0.01%): {dist['small_holders']:.2f}%")
                    
                    # Print top holders
                    if holder_data["top_holders"]:
                        logger.info("\nTop 3 Holders:")
                        for i, holder in enumerate(holder_data["top_holders"][:3], 1):
                            logger.info(f"{i}. Address: {holder['address'][:8]}... Balance: {holder['balance']:.2f}")
            return True
        except Exception as e:
            logger.error(f"❌ Holder Analysis Failed: {str(e)}")
            return False

    async def test_transaction_monitoring(self):
        """Test transaction monitoring functionality"""
        logger.info("\n💱 Testing Transaction Monitoring...")
        try:
            # Monitor transactions for the last hour
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            for token_type, tokens in self.test_tokens.items():
                logger.info(f"\nMonitoring {token_type} token transactions:")
                for token in tokens:
                    tx_data = await self.transaction_monitor.get_token_transactions(
                        token,
                        start_time=start_time,
                        end_time=end_time
                    )
                    logger.info(f"Token: {token}")
                    logger.info(f"Transaction Count: {tx_data['total_transactions']}")
                    logger.info(f"Buy/Sell Ratio: {tx_data['buy_sell_ratio']:.2f}")
                    logger.info(f"Average Transaction Size: {tx_data['avg_tx_size']:.2f}")
            return True
        except Exception as e:
            logger.error(f"❌ Transaction Monitoring Failed: {str(e)}")
            return False

async def main():
    """Run all core function tests"""
    async with CoreFunctionTester() as tester:
        try:
            results = {
                "timestamp": datetime.now().isoformat(),
                "tests": {
                    "token_launch_detection": await tester.test_token_launch_detection(),
                    "market_cap_tracking": await tester.test_market_cap_tracking(),
                    "deployer_analysis": await tester.test_deployer_analysis(),
                    "holder_analysis": await tester.test_holder_analysis(),
                    "transaction_monitoring": await tester.test_transaction_monitoring()
                }
            }
            
            # Calculate success rate
            total_tests = len(results["tests"])
            successful_tests = sum(1 for result in results["tests"].values() if result)
            success_rate = (successful_tests / total_tests) * 100
            
            logger.info(f"\n📊 Test Summary:")
            logger.info(f"Total Tests: {total_tests}")
            logger.info(f"Successful: {successful_tests}")
            logger.info(f"Failed: {total_tests - successful_tests}")
            logger.info(f"Success Rate: {success_rate:.1f}%\n")
            
            # Save results to file
            with open('core_function_test_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info("📝 Results saved to core_function_test_results.json")
        except Exception as e:
            logger.error(f"❌ Test Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
