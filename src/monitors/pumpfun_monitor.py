import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import aiohttp
import json
from pathlib import Path
import tweepy
from src.config import (
    BITQUERY_API_KEY,
    SHYFT_API_KEY,
    PUMP_FUN_PROGRAM_ID,
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET
)

class WalletManager:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "backlogs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.sniper_wallets: Set[str] = set()
        self.trusted_wallets: Set[str] = set()
        self.blacklisted_deployers: Set[str] = set()
        self.load_backlogs()
    
    def load_backlogs(self):
        """Load wallet lists from storage"""
        try:
            with open(self.data_dir / "wallet_data.json", "r") as f:
                data = json.load(f)
                self.sniper_wallets = set(data.get("sniper_wallets", []))
                self.trusted_wallets = set(data.get("trusted_wallets", []))
                self.blacklisted_deployers = set(data.get("blacklisted_deployers", []))
        except FileNotFoundError:
            self.save_backlogs()  # Create initial file
    
    def save_backlogs(self):
        """Save wallet lists to storage"""
        data = {
            "sniper_wallets": list(self.sniper_wallets),
            "trusted_wallets": list(self.trusted_wallets),
            "blacklisted_deployers": list(self.blacklisted_deployers),
            "last_updated": datetime.now().isoformat()
        }
        with open(self.data_dir / "wallet_data.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def update_wallet_status(self, address: str, wallet_type: str, success: bool):
        """Update wallet classification based on performance"""
        if success and wallet_type == "deployer":
            self.blacklisted_deployers.discard(address)
            self.trusted_wallets.add(address)
        elif not success and wallet_type == "deployer":
            self.trusted_wallets.discard(address)
            self.blacklisted_deployers.add(address)
        elif not success and wallet_type == "buyer":
            self.trusted_wallets.discard(address)
            self.sniper_wallets.add(address)
        
        self.save_backlogs()

class PumpFunMonitor:
    def __init__(self):
        self.min_market_cap = 30_000  # $30k threshold
        self.max_sniper_count = 2
        self.max_insider_count = 2
        self.max_buy_ratio = 0.7
        self.max_whale_threshold = 0.08  # 8% of supply
        self.max_whale_count = 2
        self.min_deployer_success_rate = 0.03  # 3% success rate required
        self.min_successful_mcap = 3_000_000  # $3M for success
        self.min_failed_mcap = 200_000  # $200k for failure
        
        self.wallet_manager = WalletManager()
        self.twitter_api = self.setup_twitter_api()
    
    def setup_twitter_api(self):
        """Initialize Twitter API client"""
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        return tweepy.API(auth)

    async def analyze_deployer_history(self, deployer_address: str) -> Dict:
        """Analyze deployer's token creation history"""
        if deployer_address in self.wallet_manager.blacklisted_deployers:
            return {"success": False, "reason": "Blacklisted deployer"}
            
        query = """
        query ($creator: String!) {
          solana {
            tokens(
              creator: {is: $creator}
              options: {limit: 100}
            ) {
              address
              name
              symbol
              marketCap
              createdAt
            }
          }
        }
        """
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://graphql.bitquery.io",
                json={"query": query, "variables": {"creator": deployer_address}},
                headers={"X-API-KEY": BITQUERY_API_KEY}
            ) as response:
                data = await response.json()
                
                if "data" not in data or "solana" not in data["data"]:
                    return {"success": False, "reason": "Failed to fetch deployer history"}
                
                tokens = data["data"]["solana"]["tokens"]
                total_tokens = len(tokens)
                if total_tokens == 0:
                    return {"success": True, "reason": "New deployer"}
                
                successful_tokens = sum(1 for t in tokens if float(t.get("marketCap", 0)) > self.min_successful_mcap)
                failed_tokens = sum(1 for t in tokens if float(t.get("marketCap", 0)) < self.min_failed_mcap)
                
                failure_rate = failed_tokens / total_tokens if total_tokens > 0 else 0
                if failure_rate > 0.97:  # 97% of tokens failed
                    self.wallet_manager.update_wallet_status(deployer_address, "deployer", False)
                    return {"success": False, "reason": "High failure rate"}
                
                return {
                    "success": True,
                    "total_tokens": total_tokens,
                    "successful_tokens": successful_tokens,
                    "failed_tokens": failed_tokens
                }

    async def analyze_holders(self, token_address: str) -> Dict:
        """Analyze token holder distribution and behavior"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.shyft.to/sol/v1/token/holders?network=mainnet-beta&token_address={token_address}",
                headers={"x-api-key": SHYFT_API_KEY}
            ) as response:
                data = await response.json()
                
                if "result" not in data:
                    return {"success": False, "reason": "Failed to fetch holder data"}
                
                holders = data["result"]
                total_supply = sum(float(h.get("amount", 0)) for h in holders)
                
                # Check whale concentration
                whale_count = sum(1 for h in holders if float(h.get("amount", 0)) / total_supply > self.max_whale_threshold)
                if whale_count > self.max_whale_count:
                    return {"success": False, "reason": "Excessive whale concentration"}
                
                # Check sniper/insider activity
                sniper_count = sum(1 for h in holders if h["owner"] in self.wallet_manager.sniper_wallets)
                insider_count = sum(1 for h in holders if h["owner"] in self.wallet_manager.trusted_wallets)
                
                if sniper_count > self.max_sniper_count:
                    return {"success": False, "reason": "Excessive sniper activity"}
                if insider_count > self.max_insider_count:
                    return {"success": False, "reason": "Excessive insider activity"}
                
                return {
                    "success": True,
                    "total_holders": len(holders),
                    "whale_count": whale_count,
                    "sniper_count": sniper_count,
                    "insider_count": insider_count
                }

    async def analyze_twitter_sentiment(self, token_address: str) -> Dict:
        """Analyze Twitter mentions and sentiment"""
        try:
            # Search for token mentions
            tweets = self.twitter_api.search_tweets(q=token_address, count=100)
            
            # Analyze notable mentions (accounts with >10k followers)
            notable_mentions = [
                tweet for tweet in tweets
                if tweet.user.followers_count > 10000
            ]
            
            # Check for official account
            token_account = next(
                (tweet.user for tweet in tweets if token_address.lower() in tweet.user.description.lower()),
                None
            )
            
            name_changes = 0
            if token_account:
                timeline = self.twitter_api.user_timeline(user_id=token_account.id, count=100)
                name_changes = sum(1 for tweet in timeline if hasattr(tweet, 'retweeted_status'))
            
            return {
                "success": True,
                "notable_mentions": len(notable_mentions),
                "name_changes": name_changes,
                "sentiment_score": len(notable_mentions) / 100 if notable_mentions else 0
            }
        except Exception as e:
            return {"success": False, "reason": f"Twitter analysis failed: {str(e)}"}

    async def analyze_top_holders(self, token_address: str) -> Dict:
        """Analyze performance of top token holders"""
        async with aiohttp.ClientSession() as session:
            # Get top 30 holders
            async with session.get(
                f"https://api.shyft.to/sol/v1/token/holders?network=mainnet-beta&token_address={token_address}&limit=30",
                headers={"x-api-key": SHYFT_API_KEY}
            ) as response:
                data = await response.json()
                
                if "result" not in data:
                    return {"success": False, "reason": "Failed to fetch top holders"}
                
                holders = data["result"]
                
                # Analyze each holder's performance
                holder_stats = []
                for holder in holders:
                    # Skip developer and liquidity addresses
                    if await self.is_known_address(holder["owner"]):
                        continue
                    
                    # Get holder's transaction history
                    async with session.get(
                        f"https://api.shyft.to/sol/v1/wallet/transactions?network=mainnet-beta&wallet={holder['owner']}&history=30",
                        headers={"x-api-key": SHYFT_API_KEY}
                    ) as tx_response:
                        tx_data = await tx_response.json()
                        
                        if "result" not in tx_data:
                            continue
                        
                        transactions = tx_data["result"]
                        
                        # Calculate success rate
                        successful_trades = 0
                        total_trades = 0
                        
                        for tx in transactions:
                            if tx.get("type") == "TOKEN_TRANSFER":
                                total_trades += 1
                                if float(tx.get("amount", 0)) > self.min_successful_mcap:
                                    successful_trades += 1
                        
                        win_rate = successful_trades / total_trades if total_trades > 0 else 0
                        holder_stats.append({
                            "address": holder["owner"],
                            "win_rate": win_rate,
                            "total_trades": total_trades
                        })
                
                return {
                    "success": True,
                    "top_holders": holder_stats,
                    "average_win_rate": sum(h["win_rate"] for h in holder_stats) / len(holder_stats) if holder_stats else 0
                }

    async def monitor_new_launches(self, callback) -> None:
        """Monitor new token launches on pump.fun"""
        while True:
            try:
                # Get new token launches
                tokens = await self.get_bitquery_token_data(PUMP_FUN_PROGRAM_ID)
                
                for token in tokens:
                    # Skip if market cap below threshold
                    market_cap = await self.get_market_cap(token["address"])
                    if market_cap < self.min_market_cap:
                        continue
                    
                    # Run analysis pipeline
                    deployer_analysis = await self.analyze_deployer_history(token["creator"])
                    if not deployer_analysis["success"]:
                        continue
                    
                    holder_analysis = await self.analyze_holders(token["address"])
                    if not holder_analysis["success"]:
                        continue
                    
                    twitter_analysis = await self.analyze_twitter_sentiment(token["address"])
                    top_holder_analysis = await self.analyze_top_holders(token["address"])
                    
                    # Calculate final confidence score
                    confidence_score = await self.calculate_confidence_score(
                        deployer_analysis,
                        holder_analysis,
                        twitter_analysis,
                        top_holder_analysis
                    )
                    
                    # Send results to callback
                    await callback({
                        "token_address": token["address"],
                        "market_cap": market_cap,
                        "confidence_score": confidence_score,
                        "analyses": {
                            "deployer": deployer_analysis,
                            "holders": holder_analysis,
                            "twitter": twitter_analysis,
                            "top_holders": top_holder_analysis
                        }
                    })
                
                # Update backlogs
                self.wallet_manager.save_backlogs()
                
            except Exception as e:
                print(f"Error in monitor loop: {str(e)}")
            
            await asyncio.sleep(60)  # Check every minute

    async def calculate_confidence_score(
        self,
        deployer_analysis: Dict,
        holder_analysis: Dict,
        twitter_analysis: Dict,
        top_holder_analysis: Dict
    ) -> float:
        """Calculate overall confidence score"""
        score = 0
        
        # Deployer score (30%)
        if deployer_analysis["success"]:
            success_rate = deployer_analysis["successful_tokens"] / deployer_analysis["total_tokens"]
            score += 0.3 * min(success_rate * 100, 100)
        
        # Holder analysis (30%)
        if holder_analysis["success"]:
            holder_score = 100
            holder_score -= (holder_analysis["whale_count"] / self.max_whale_count) * 50
            holder_score -= (holder_analysis["sniper_count"] / self.max_sniper_count) * 30
            holder_score -= (holder_analysis["insider_count"] / self.max_insider_count) * 20
            score += 0.3 * max(holder_score, 0)
        
        # Twitter sentiment (20%)
        if twitter_analysis["success"]:
            sentiment_score = min(twitter_analysis["notable_mentions"] * 10, 100)
            sentiment_score -= twitter_analysis["name_changes"] * 10
            score += 0.2 * max(sentiment_score, 0)
        
        # Top holder performance (20%)
        if top_holder_analysis["success"]:
            win_rate = top_holder_analysis["average_win_rate"]
            score += 0.2 * min(win_rate * 100, 100)
        
        return score

    async def get_bitquery_token_data(self, token_address: str) -> Dict:
        """
        Get token data from Bitquery
        """
        query = """
        query ($token: String!) {
          solana {
            transfers(
              options: {limit: 100}
              token: {address: {is: $token}}
            ) {
              amount
              block {
                timestamp {
                  time(format: "%Y-%m-%d %H:%M:%S")
                }
                height
              }
              sender {
                address
              }
              receiver {
                address
              }
            }
            trades: dexTrades(
              options: {limit: 100, desc: "block.height"}
              baseCurrency: {is: $token}
            ) {
              transaction {
                hash
              }
              block {
                height
                timestamp {
                  time(format: "%Y-%m-%d %H:%M:%S")
                }
              }
              side
              price
              amount
              maker {
                address
              }
              taker {
                address
              }
            }
          }
        }
        """
        
        headers = {
            "X-API-KEY": BITQUERY_API_KEY,
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://graphql.bitquery.io",
                json={"query": query, "variables": {"token": token_address}},
                headers=headers
            ) as response:
                return await response.json()

    async def get_shyft_token_data(self, token_address: str) -> Dict:
        """
        Get token data from SHYFT
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.shyft.to/sol/v1/token/get_info?network=mainnet-beta&token_address={token_address}",
                headers={"x-api-key": SHYFT_API_KEY}
            ) as response:
                return await response.json()

    async def get_market_cap(self, token_address: str) -> float:
        """
        Calculate token's market cap
        """
        try:
            # Get token data from SHYFT
            token_data = await self.get_shyft_token_data(token_address)
            
            # Get latest trade from Bitquery
            trade_data = await self.get_bitquery_token_data(token_address)
            
            if not token_data.get("result") or not trade_data.get("data"):
                return 0
                
            supply = float(token_data["result"]["supply"])
            
            # Get latest price
            trades = trade_data["data"]["solana"]["trades"]
            if not trades:
                return 0
                
            latest_price = float(trades[0]["price"])
            
            return supply * latest_price
            
        except Exception as e:
            print(f"Error calculating market cap: {str(e)}")
            return 0

    async def analyze_transaction_ratios(self, token_address: str) -> Dict:
        """
        Analyze buy/sell transaction ratios
        """
        try:
            trade_data = await self.get_bitquery_token_data(token_address)
            
            if not trade_data.get("data"):
                return {"is_suspicious": True, "reason": "No trade data available"}
                
            trades = trade_data["data"]["solana"]["trades"]
            
            if not trades:
                return {"is_suspicious": True, "reason": "No trades found"}
                
            buy_count = sum(1 for t in trades if t["side"] == "BUY")
            total_trades = len(trades)
            
            if total_trades == 0:
                return {"is_suspicious": True, "reason": "No trades found"}
                
            buy_ratio = buy_count / total_trades
            
            return {
                "is_suspicious": buy_ratio > self.max_buy_ratio,
                "buy_ratio": buy_ratio,
                "total_trades": total_trades
            }
            
        except Exception as e:
            print(f"Error analyzing transaction ratios: {str(e)}")
            return {"is_suspicious": True, "reason": str(e)}

    async def check_whale_concentration(self, token_address: str) -> Dict:
        """
        Check for whale wallet concentration
        """
        try:
            # Get holder data from SHYFT
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.shyft.to/sol/v1/token/holders?network=mainnet-beta&token_address={token_address}",
                    headers={"x-api-key": SHYFT_API_KEY}
                ) as response:
                    data = await response.json()
                    
            if not data.get("result"):
                return {"is_suspicious": True, "reason": "No holder data available"}
                
            holders = data["result"]
            total_supply = sum(float(h["amount"]) for h in holders)
            
            if total_supply == 0:
                return {"is_suspicious": True, "reason": "Invalid total supply"}
                
            # Count whales (excluding known addresses)
            whale_count = sum(
                1 for h in holders
                if float(h["amount"]) / total_supply > self.max_whale_threshold
                and not self.is_known_address(h["owner"])  # Implement this method
            )
            
            return {
                "is_suspicious": whale_count > self.max_whale_count,
                "whale_count": whale_count,
                "total_holders": len(holders)
            }
            
        except Exception as e:
            print(f"Error checking whale concentration: {str(e)}")
            return {"is_suspicious": True, "reason": str(e)}

    def is_known_address(self, address: str) -> bool:
        """
        Check if address is a known system address (liquidity, burn, etc.)
        """
        # Implement address checking logic
        # Should maintain a list of known system addresses
        return False  # Placeholder
