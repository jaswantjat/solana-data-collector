import aiohttp
import asyncio
import json
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional
import pytz
from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI
from ..analysis.token_analyzer import TokenAnalyzer
import os
import aiohttp

logger = logging.getLogger(__name__)

class TokenCollector:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.analyzer = TokenAnalyzer()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.pump_fun_program = os.getenv("PUMP_FUN_PROGRAM_ID")
        
    async def fetch_tokens(self) -> List[Dict]:
        """Fetch new token launches from pump.fun"""
        try:
            # Get recent transactions for pump.fun program
            transactions = await self.helius.get_wallet_history(self.pump_fun_program)
            
            # Extract token mints from transactions
            tokens = {}
            for tx in transactions:
                # Look for token creation instructions
                for instruction in tx.get("instructions", []):
                    if instruction.get("programId") == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":  # Token Program
                        if instruction.get("name") == "initializeMint":
                            mint = instruction.get("accounts", [])[0]
                            if mint:
                                # Get token metadata
                                metadata = await self.helius.get_token_metadata(mint)
                                if metadata:
                                    # Get price and liquidity info
                                    price_info = await self.jupiter.get_token_price(mint)
                                    liquidity_info = await self.jupiter.get_token_liquidity(mint)
                                    
                                    tokens[mint] = {
                                        "address": mint,
                                        "name": metadata.get("name"),
                                        "symbol": metadata.get("symbol"),
                                        "decimals": metadata.get("decimals"),
                                        "price_usd": price_info.get("price", 0),
                                        "market_cap": price_info.get("price", 0) * metadata.get("supply", 0),
                                        "liquidity_usd": liquidity_info.get("liquidityUsd", 0),
                                        "deployer": tx.get("feePayer"),  # Usually the deployer pays the fee
                                        "created_at": tx.get("timestamp")
                                    }
            
            return list(tokens.values())
            
        except Exception as e:
            logger.error(f"Error fetching tokens: {str(e)}")
            return []
            
    async def send_discord_notification(self, token_data: Dict, analysis: Dict):
        """Send token analysis to Discord webhook"""
        try:
            if not self.discord_webhook:
                logger.warning("Discord webhook URL not configured")
                return
                
            embed = {
                "title": f"New Token Alert: {token_data['symbol']}",
                "description": f"Contract: {token_data['address']}",
                "color": 5814783,
                "fields": [
                    {
                        "name": "Confidence Score",
                        "value": f"{analysis['confidence_score']:.2f}%",
                        "inline": True
                    },
                    {
                        "name": "Market Cap",
                        "value": f"${token_data['market_cap']:,.2f}",
                        "inline": True
                    },
                    {
                        "name": "Liquidity",
                        "value": f"${token_data['liquidity_usd']:,.2f}",
                        "inline": True
                    },
                    {
                        "name": "Holder Count",
                        "value": str(analysis['analysis']['holders']['holder_count']),
                        "inline": True
                    },
                    {
                        "name": "Deployer Success Rate",
                        "value": f"{(1 - analysis['analysis']['deployer']['failure_rate']) * 100:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "Twitter Sentiment",
                        "value": f"{analysis['analysis']['twitter']['sentiment']:.2f}",
                        "inline": True
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.discord_webhook,
                    json={"embeds": [embed]}
                )
                
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            
    async def update_data(self):
        """Update all token data"""
        try:
            # Fetch new tokens
            tokens = await self.fetch_tokens()
            
            # Filter and analyze tokens
            analyzed_tokens = {}
            for token in tokens:
                # Check market cap threshold
                if token.get("market_cap", 0) > 30000:
                    # Analyze token
                    analysis = await self.analyzer.analyze_token(
                        token["address"],
                        token.get("deployer")
                    )
                    
                    if analysis["status"] == "success":
                        analyzed_tokens[token["address"]] = {
                            "token": token,
                            "analysis": analysis
                        }
                        
                        # Send Discord notification if confidence score is high
                        if analysis["confidence_score"] > 70:
                            await self.send_discord_notification(token, analysis)
                            
            # Save analyzed tokens
            analysis_file = self.data_dir / "analyzed_tokens.json"
            with open(analysis_file, 'w') as f:
                json.dump(analyzed_tokens, f, indent=2)
                
            logger.info(f"Successfully analyzed {len(analyzed_tokens)} tokens")
            
        except Exception as e:
            logger.error(f"Error updating data: {str(e)}")

async def start_collector():
    """Start the token collector"""
    collector = TokenCollector()
    while True:
        await collector.update_data()
        await asyncio.sleep(60)  # Update every minute
