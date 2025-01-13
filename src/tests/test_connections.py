import os
import sys
import asyncio
import aiohttp
from dotenv import load_dotenv
import tweepy
from discord_webhook import DiscordWebhook

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

async def test_shyft_connection():
    """Test SHYFT API connection"""
    print("\nTesting SHYFT API connection...")
    async with aiohttp.ClientSession() as session:
        url = "https://api.shyft.to/sol/v1/token/get_info"
        params = {
            "network": "mainnet-beta",
            "token_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        }
        headers = {"x-api-key": os.getenv("SHYFT_API_KEY")}
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()
                if response.status == 200:
                    print("✅ SHYFT API connection successful!")
                else:
                    print("❌ SHYFT API error:", data.get("message", "Unknown error"))
        except Exception as e:
            print("❌ SHYFT API error:", str(e))

async def test_bitquery_connection():
    """Test Bitquery API connection"""
    print("\nTesting Bitquery API connection...")
    query = """
    {
      solana {
        transfers(options: {limit: 1}) {
          amount
          block {
            timestamp {
              time(format: "%Y-%m-%d %H:%M:%S")
            }
          }
        }
      }
    }
    """
    
    headers = {
        "X-API-KEY": os.getenv("BITQUERY_API_KEY"),
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://graphql.bitquery.io",
                json={"query": query},
                headers=headers
            ) as response:
                data = await response.json()
                if "data" in data:
                    print("✅ Bitquery API connection successful!")
                else:
                    print("❌ Bitquery API error:", data.get("errors", ["Unknown error"])[0].get("message"))
    except Exception as e:
        print("❌ Bitquery API error:", str(e))

def test_twitter_connection():
    """Test Twitter API connection"""
    print("\nTesting Twitter API connection...")
    try:
        client = tweepy.Client(
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            wait_on_rate_limit=True
        )
        
        # Test search
        tweets = client.search_recent_tweets(query="solana", max_results=10)
        if tweets.data:
            print("✅ Twitter API connection successful!")
        else:
            print("⚠️ Twitter API connected but no tweets found")
    except Exception as e:
        print("❌ Twitter API error:", str(e))

def test_discord_webhook():
    """Test Discord webhook"""
    print("\nTesting Discord webhook...")
    try:
        webhook = DiscordWebhook(
            url=os.getenv("DISCORD_WEBHOOK_URL"),
            content="🤖 Test message from Solana Token Monitor"
        )
        response = webhook.execute()
        
        if response.status_code in [200, 204]:  # Both are success codes for Discord
            print("✅ Discord webhook successful!")
        else:
            print("❌ Discord webhook error:", response.status_code)
    except Exception as e:
        print("❌ Discord webhook error:", str(e))

async def main():
    """Run all connection tests"""
    print("🔍 Testing API connections...")
    
    # Test all connections
    await test_shyft_connection()
    await test_bitquery_connection()
    test_twitter_connection()
    test_discord_webhook()

if __name__ == "__main__":
    asyncio.run(main())
