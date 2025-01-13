import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI
from ..integrations.twitter import TwitterAPI
from .wallet_tracker import WalletTracker
from .supply_analyzer import SupplyAnalyzer

logger = logging.getLogger(__name__)

class TokenAnalyzer:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.twitter = TwitterAPI()
        self.wallet_tracker = WalletTracker()
        self.supply_analyzer = SupplyAnalyzer()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.blacklist_file = self.data_dir / "blacklist.json"
        self._load_blacklist()
        
    def _load_blacklist(self):
        """Load blacklist data"""
        try:
            if self.blacklist_file.exists():
                with open(self.blacklist_file, 'r') as f:
                    self.blacklist = json.load(f)
            else:
                self.blacklist = {"deployers": [], "tokens": []}
                
        except Exception as e:
            logger.error(f"Error loading blacklist: {str(e)}")
            self.blacklist = {"deployers": [], "tokens": []}
            
    def _save_blacklist(self):
        """Save blacklist data"""
        try:
            with open(self.blacklist_file, 'w') as f:
                json.dump(self.blacklist, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving blacklist: {str(e)}")
            
    async def analyze_token(self, token_address: str, deployer_address: str) -> Dict:
        """Analyze a token comprehensively"""
        try:
            # Check blacklist
            if deployer_address in self.blacklist["deployers"]:
                return {"status": "rejected", "reason": "blacklisted_deployer"}
                
            if token_address in self.blacklist["tokens"]:
                return {"status": "rejected", "reason": "blacklisted_token"}
                
            # 1. Deployer History Check
            deployer_analysis = await self._analyze_deployer(deployer_address)
            if not deployer_analysis["passed"]:
                self.blacklist["deployers"].append(deployer_address)
                self._save_blacklist()
                return {"status": "rejected", "reason": "deployer_history"}
                
            # 2. Supply Distribution Check
            supply_analysis = await self.supply_analyzer.analyze_supply_distribution(token_address)
            if supply_analysis.get("whale_count", 0) > 2:
                return {"status": "rejected", "reason": "whale_concentration"}
                
            # 3. Holder & Transaction Analysis
            holder_analysis = await self._analyze_holders(token_address, deployer_address)
            if not holder_analysis["passed"]:
                return {"status": "rejected", "reason": "holder_analysis"}
                
            # 4. Twitter Analysis
            twitter_analysis = await self._analyze_twitter(token_address)
            
            # 5. Top Holder Analysis
            top_holder_analysis = await self._analyze_top_holders(token_address)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                deployer_analysis,
                supply_analysis,
                holder_analysis,
                twitter_analysis,
                top_holder_analysis
            )
            
            return {
                "status": "success",
                "confidence_score": confidence_score,
                "analysis": {
                    "deployer": deployer_analysis,
                    "supply": supply_analysis,
                    "holders": holder_analysis,
                    "twitter": twitter_analysis,
                    "top_holders": top_holder_analysis
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing token: {str(e)}")
            return {"status": "error", "reason": str(e)}
            
    async def _analyze_deployer(self, deployer_address: str) -> Dict:
        """Analyze deployer history"""
        try:
            # Get deployer's transaction history
            transactions = await self.helius.get_wallet_history(deployer_address)
            
            # Find token deployments
            token_deployments = []
            for tx in transactions:
                if "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" in tx.get("programIds", []):
                    for ix in tx.get("instructions", []):
                        if ix.get("name") == "initializeMint":
                            token_deployments.append({
                                "token": ix.get("accounts", [])[0],
                                "timestamp": tx.get("timestamp")
                            })
                            
            if not token_deployments:
                return {"passed": True, "reason": "new_deployer"}
                
            # Analyze past tokens' performance
            failed_tokens = 0
            successful_tokens = 0
            
            for deployment in token_deployments:
                # Get token price info
                price_info = await self.jupiter.get_token_price(deployment["token"])
                liquidity_info = await self.jupiter.get_token_liquidity(deployment["token"])
                
                market_cap = price_info.get("price", 0) * liquidity_info.get("totalSupply", 0)
                
                if market_cap < 200000:
                    failed_tokens += 1
                elif market_cap > 3000000:
                    successful_tokens += 1
                    
            failure_rate = failed_tokens / len(token_deployments) if token_deployments else 0
            
            return {
                "passed": failure_rate < 0.97,
                "failure_rate": failure_rate,
                "total_deployments": len(token_deployments),
                "successful_tokens": successful_tokens
            }
            
        except Exception as e:
            logger.error(f"Error analyzing deployer: {str(e)}")
            return {"passed": False, "reason": "analysis_error"}
            
    async def _analyze_holders(self, token_address: str, deployer_address: str) -> Dict:
        """Analyze token holders and transactions"""
        try:
            # Get holder data
            holders = await self.helius.get_token_holders(token_address)
            
            # Get recent transfers
            transfers = await self.helius.get_token_transfers(token_address)
            
            # Count unique buyers and sellers
            buyers = set()
            sellers = set()
            sniper_count = 0
            insider_count = 0
            deployer_sold = False
            
            for transfer in transfers:
                buyer = transfer.get("receiver", {}).get("address")
                seller = transfer.get("sender", {}).get("address")
                
                if buyer:
                    buyers.add(buyer)
                    # Check if buyer is a known sniper
                    if self.wallet_tracker.is_sniper(buyer):
                        sniper_count += 1
                    # Check if buyer is a known insider
                    if buyer in [h.get("address") for h in holders[:5]]:
                        insider_count += 1
                        
                if seller:
                    sellers.add(seller)
                    # Check if deployer sold
                    if seller == deployer_address:
                        deployer_sold = True
                        
            # Calculate buy/sell ratio
            total_transactions = len(buyers) + len(sellers)
            buy_ratio = len(buyers) / total_transactions if total_transactions > 0 else 0
            
            # Update wallet classifications
            for address in buyers | sellers:
                await self.wallet_tracker.update_wallet_classification(address)
                
            passed = (
                sniper_count <= 2 and
                insider_count <= 2 and
                buy_ratio <= 0.7 and
                not deployer_sold
            )
            
            return {
                "passed": passed,
                "holder_count": len(holders),
                "sniper_count": sniper_count,
                "insider_count": insider_count,
                "buy_ratio": buy_ratio,
                "deployer_sold": deployer_sold
            }
            
        except Exception as e:
            logger.error(f"Error analyzing holders: {str(e)}")
            return {"passed": False, "reason": "analysis_error"}
            
    async def _analyze_twitter(self, token_address: str) -> Dict:
        """Analyze Twitter presence and sentiment"""
        try:
            # Get Twitter mentions and sentiment
            twitter_data = await self.twitter.analyze_token_mentions(token_address)
            
            # Get notable mentions
            notable_mentions = []
            for mention in twitter_data.get("notable_mentions", []):
                if mention.get("followers_count", 0) > 100000:
                    notable_mentions.append({
                        "username": mention.get("username"),
                        "followers": mention.get("followers_count"),
                        "verified": mention.get("verified", False)
                    })
                    
            return {
                "mention_count": twitter_data.get("total_mentions", 0),
                "sentiment": twitter_data.get("average_sentiment", 0),
                "notable_mentions": notable_mentions,
                "engagement_score": twitter_data.get("engagement_score", 0)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Twitter: {str(e)}")
            return {"mention_count": 0, "sentiment": 0, "notable_mentions": []}
            
    async def _analyze_top_holders(self, token_address: str) -> Dict:
        """Analyze top holder performance"""
        try:
            # Get top 30 holders
            supply_analysis = await self.supply_analyzer.analyze_supply_distribution(token_address)
            top_holders = supply_analysis.get("holders", [])[:30]
            
            successful_holders = 0
            total_pnl = 0
            
            for holder in top_holders:
                address = holder.get("address")
                stats = self.wallet_tracker.get_wallet_stats(address)
                
                if stats:
                    if stats.get("metrics", {}).get("win_rate", 0) > 0.5:
                        successful_holders += 1
                    total_pnl += stats.get("metrics", {}).get("total_pnl", 0)
                    
            return {
                "successful_holders": successful_holders,
                "average_win_rate": successful_holders / len(top_holders) if top_holders else 0,
                "average_pnl": total_pnl / len(top_holders) if top_holders else 0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing top holders: {str(e)}")
            return {"successful_holders": 0, "average_win_rate": 0, "average_pnl": 0}
            
    def _calculate_confidence_score(self, deployer_analysis: Dict,
                                 supply_analysis: Dict,
                                 holder_analysis: Dict,
                                 twitter_analysis: Dict,
                                 top_holder_analysis: Dict) -> float:
        """Calculate overall confidence score"""
        try:
            # Deployer score (25%)
            deployer_score = (
                (1 - deployer_analysis["failure_rate"]) * 100 * 0.25
            )
            
            # Supply distribution score (25%)
            supply_score = supply_analysis.get("distribution_score", 0) * 0.25
            
            # Holder analysis score (20%)
            holder_score = (
                (1 - holder_analysis["buy_ratio"]) * 50 +  # Lower buy ratio is better
                (min(holder_analysis["holder_count"], 1000) / 1000) * 50  # More holders is better
            ) * 0.2
            
            # Twitter score (15%)
            twitter_score = (
                min(twitter_analysis["mention_count"], 100) / 100 * 40 +  # Mentions
                (twitter_analysis["sentiment"] + 1) / 2 * 30 +  # Sentiment (-1 to 1)
                min(len(twitter_analysis["notable_mentions"]), 5) / 5 * 30  # Notable mentions
            ) * 0.15
            
            # Top holder score (15%)
            top_holder_score = (
                top_holder_analysis["average_win_rate"] * 100 * 0.15
            )
            
            return min(100, deployer_score + supply_score + holder_score + twitter_score + top_holder_score)
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0
