import asyncio
from typing import Dict
from datetime import datetime
from .pumpfun_monitor import PumpFunMonitor
from ..analyzers.confidence_analyzer import ConfidenceAnalyzer
from ..analyzers.suspicious_activity_analyzer import SuspiciousActivityAnalyzer
from ..managers.blacklist_manager import BlacklistManager
from ..collectors.deployer_analyzer import DeployerAnalyzer
from ..collectors.holder_analyzer import HolderAnalyzer
from ..collectors.twitter_analyzer import TwitterAnalyzer

class TokenMonitor:
    def __init__(self):
        self.pumpfun_monitor = PumpFunMonitor()
        self.confidence_analyzer = ConfidenceAnalyzer()
        self.suspicious_analyzer = SuspiciousActivityAnalyzer()
        self.blacklist_manager = BlacklistManager()
        self.deployer_analyzer = DeployerAnalyzer()
        self.holder_analyzer = HolderAnalyzer()
        self.twitter_analyzer = TwitterAnalyzer()

    async def handle_new_token(self, token_data: Dict) -> None:
        """
        Handle new token detection
        """
        token_address = token_data["token_address"]
        market_cap = token_data["market_cap"]
        
        print(f"\nAnalyzing new token: {token_address}")
        print(f"Current Market Cap: ${market_cap:,.2f}")
        
        # Skip if market cap is too low
        if market_cap < self.pumpfun_monitor.min_market_cap:
            print("Market cap below threshold, skipping analysis")
            return
            
        # Get deployer data
        deployer_address = token_data["transfer_data"]["sender"]["address"]
        
        # Check if deployer is blacklisted
        if self.blacklist_manager.is_blacklisted(deployer_address):
            print(f"Deployer {deployer_address} is blacklisted, skipping analysis")
            return
            
        # Analyze deployer history
        deployer_data = await self.deployer_analyzer.analyze_deployer_history(deployer_address)
        
        # Check deployer success rate
        if not self._check_deployer_success_rate(deployer_data):
            print("Deployer success rate too low, skipping analysis")
            return
            
        # Analyze holder distribution
        holder_data = await self.holder_analyzer.get_token_holders(token_address)
        
        # Check whale concentration
        whale_check = await self.pumpfun_monitor.check_whale_concentration(token_address)
        if whale_check["is_suspicious"]:
            print(f"Suspicious whale concentration: {whale_check['whale_count']} whales")
            return
            
        # Analyze transaction patterns
        tx_analysis = await self.pumpfun_monitor.analyze_transaction_ratios(token_address)
        if tx_analysis["is_suspicious"]:
            print(f"Suspicious transaction ratios: {tx_analysis['buy_ratio']:.1%} buys")
            return
            
        # Check for sniper/insider activity
        sniper_data = await self.holder_analyzer.identify_sniper_purchases(token_address)
        if len(sniper_data["snipers"]) > self.pumpfun_monitor.max_sniper_count:
            print(f"Too many snipers detected: {len(sniper_data['snipers'])}")
            return
            
        # Analyze Twitter sentiment
        twitter_data = await self.twitter_analyzer.analyze_token_twitter(token_address)
        
        # Compile all data
        analysis_data = {
            "token_address": token_address,
            "market_cap": market_cap,
            "deployer_data": deployer_data,
            "holder_data": holder_data,
            "transaction_analysis": tx_analysis,
            "whale_analysis": whale_check,
            "sniper_data": sniper_data,
            "twitter_data": twitter_data
        }
        
        # Check for suspicious activity
        suspicious_analysis = await self.suspicious_analyzer.analyze_suspicious_activity(
            token_address,
            analysis_data
        )
        
        if suspicious_analysis["is_suspicious"]:
            print("Suspicious activity detected, updating blacklist")
            await self.blacklist_manager.add_to_blacklist(
                deployer_address,
                "Suspicious token activity",
                suspicious_analysis
            )
            return
            
        # Calculate confidence score
        confidence_score = self.confidence_analyzer.calculate_confidence_score(analysis_data)
        
        if confidence_score >= self.confidence_analyzer.threshold:
            print(f"High confidence token detected! Score: {confidence_score:.1f}")
            # Send Discord notification
            await self.confidence_analyzer.send_discord_notification(
                token_address,
                analysis_data,
                confidence_score
            )
        else:
            print(f"Token confidence score too low: {confidence_score:.1f}")

    def _check_deployer_success_rate(self, deployer_data: Dict) -> bool:
        """
        Check if deployer meets minimum success rate requirements
        """
        total_tokens = deployer_data.get("total_tokens", 0)
        if total_tokens == 0:
            return True  # New deployer
            
        successful_tokens = sum(
            1 for t in deployer_data.get("tokens", [])
            if t.get("max_market_cap", 0) >= self.pumpfun_monitor.min_successful_mcap
        )
        
        failed_tokens = sum(
            1 for t in deployer_data.get("tokens", [])
            if t.get("max_market_cap", 0) < self.pumpfun_monitor.min_failed_mcap
        )
        
        if total_tokens > 0:
            failure_rate = failed_tokens / total_tokens
            if failure_rate > (1 - self.pumpfun_monitor.min_deployer_success_rate):
                return False
                
        return True

async def main():
    """
    Main monitoring loop
    """
    monitor = TokenMonitor()
    
    print("Starting pump.fun token monitor...")
    print("Monitoring for new tokens with market cap > $30,000")
    
    await monitor.pumpfun_monitor.monitor_new_launches(monitor.handle_new_token)

if __name__ == "__main__":
    asyncio.run(main())
