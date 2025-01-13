import asyncio
import os
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from discord_webhook import DiscordWebhook, DiscordEmbed
from src.monitors.pumpfun_monitor import PumpFunMonitor
from src.config import (
    DISCORD_WEBHOOK_URL,
    MIN_MARKET_CAP,
    CONFIDENCE_SCORE_THRESHOLD,
    POLLING_INTERVAL
)

class TokenMonitor:
    def __init__(self):
        self.monitor = PumpFunMonitor()
        self.discord_webhook_url = DISCORD_WEBHOOK_URL
        
    async def send_discord_alert(self, analysis_data: Dict, color: int = 0x00ff00):
        """Send detailed analysis to Discord"""
        try:
            # Create embed
            embed = DiscordEmbed(
                title="🎯 New Token Analysis",
                description=f"Analysis results for token launched on pump.fun",
                color=color
            )
            
            # Add token info
            embed.add_embed_field(
                name="Token Info",
                value=(
                    f"**Address**: `{analysis_data['token_address']}`\n"
                    f"**Market Cap**: ${analysis_data['market_cap']:,.2f}\n"
                    f"**Confidence Score**: {analysis_data['confidence_score']:.1f}%"
                ),
                inline=False
            )
            
            # Add deployer analysis
            deployer = analysis_data["analyses"]["deployer"]
            if deployer["success"]:
                embed.add_embed_field(
                    name="👨‍💻 Deployer Analysis",
                    value=(
                        f"**Total Tokens**: {deployer['total_tokens']}\n"
                        f"**Success Rate**: {(deployer['successful_tokens']/deployer['total_tokens']*100):.1f}%"
                    ),
                    inline=True
                )
            
            # Add holder analysis
            holders = analysis_data["analyses"]["holders"]
            if holders["success"]:
                embed.add_embed_field(
                    name="👥 Holder Analysis",
                    value=(
                        f"**Total Holders**: {holders['total_holders']}\n"
                        f"**Whale Count**: {holders['whale_count']}\n"
                        f"**Sniper Count**: {holders['sniper_count']}"
                    ),
                    inline=True
                )
            
            # Add Twitter analysis
            twitter = analysis_data["analyses"]["twitter"]
            if twitter["success"]:
                embed.add_embed_field(
                    name="🐦 Twitter Analysis",
                    value=(
                        f"**Notable Mentions**: {twitter['notable_mentions']}\n"
                        f"**Name Changes**: {twitter['name_changes']}\n"
                        f"**Sentiment Score**: {twitter['sentiment_score']:.1f}"
                    ),
                    inline=True
                )
            
            # Add top holder analysis
            top_holders = analysis_data["analyses"]["top_holders"]
            if top_holders["success"]:
                embed.add_embed_field(
                    name="🏆 Top Holder Analysis",
                    value=(
                        f"**Average Win Rate**: {top_holders['average_win_rate']*100:.1f}%"
                    ),
                    inline=True
                )
            
            # Add timestamp and links
            embed.set_timestamp(datetime.now().isoformat())
            embed.add_embed_field(
                name="🔗 Links",
                value=(
                    f"[View on Solscan](https://solscan.io/token/{analysis_data['token_address']})\n"
                    f"[View on Birdeye](https://birdeye.so/token/{analysis_data['token_address']})"
                ),
                inline=False
            )
            
            # Send webhook
            webhook = DiscordWebhook(url=self.discord_webhook_url)
            webhook.add_embed(embed)
            response = webhook.execute()
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            print(f"Error sending Discord alert: {str(e)}")
            return False

    async def handle_new_token(self, token_data: dict):
        """Handle new token detection"""
        try:
            token_address = token_data["token_address"]
            market_cap = token_data["market_cap"]
            
            print(f"\nAnalyzing token: {token_address}")
            print(f"Market Cap: ${market_cap:,.2f}")
            
            # Skip if market cap is too low
            if market_cap < MIN_MARKET_CAP:
                return
            
            # Skip if confidence score is too low
            if token_data["confidence_score"] < CONFIDENCE_SCORE_THRESHOLD:
                return
            
            # Send detailed analysis to Discord
            await self.send_discord_alert(
                token_data,
                color=0x00ff00 if token_data["confidence_score"] >= 80 else 0xffaa00
            )
            
        except Exception as e:
            print(f"Error handling token {token_data.get('token_address')}: {str(e)}")
            await self.send_discord_alert(
                {
                    "token_address": token_data.get("token_address"),
                    "error": str(e)
                },
                color=0xff0000
            )

    async def start_monitoring(self):
        """Start monitoring for new tokens"""
        print("🚀 Starting Enhanced Solana Token Monitor...")
        await self.send_discord_alert({
            "token_address": "SYSTEM",
            "market_cap": 0,
            "confidence_score": 100,
            "analyses": {
                "deployer": {"success": True},
                "holders": {"success": True},
                "twitter": {"success": True},
                "top_holders": {"success": True}
            }
        }, color=0x00ff00)
        
        try:
            await self.monitor.monitor_new_launches(self.handle_new_token)
                
        except Exception as e:
            error_msg = f"❌ Critical error in token monitor: {str(e)}"
            print(error_msg)
            await self.send_discord_alert({
                "token_address": "SYSTEM",
                "market_cap": 0,
                "confidence_score": 0,
                "error": str(e)
            }, color=0xff0000)
            raise

async def main():
    monitor = TokenMonitor()
    await monitor.start_monitoring()

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Start monitor
    asyncio.run(main())
