import asyncio
import aiohttp
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import asyncpg
import redis
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_supabase_connection():
    """Test Supabase (PostgreSQL) connection"""
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        version = await conn.fetchval('SELECT version();')
        await conn.close()
        logger.info(f"✅ Supabase Connection Successful - PostgreSQL {version}")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase Connection Failed: {str(e)}")
        return False

def test_redis_connection():
    """Test Redis connection"""
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_URL').split(':')[1].replace('//', ''),
            port=int(os.getenv('REDIS_URL').split(':')[2]),
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=True
        )
        info = r.info()
        r.close()
        logger.info(f"✅ Redis Connection Successful - Version {info['redis_version']}")
        return True
    except Exception as e:
        logger.error(f"❌ Redis Connection Failed: {str(e)}")
        return False

async def test_helius_api():
    """Test Helius API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.helius.xyz/v0/token-metadata?api-key={os.getenv('HELIUS_API_KEY')}"
            data = {
                "mintAccounts": ["7i5KKsX2weiTkry7jA4ZwSuXGhs5eJBEjY8vVxR4pfRx"]
            }
            async with session.post(url, json=data) as response:
                result = await response.json()
                if response.status == 200:
                    logger.info("✅ Helius API Connection Successful")
                    return True
                else:
                    logger.error(f"❌ Helius API Failed: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Helius API Connection Failed: {str(e)}")
        return False

async def test_shyft_api():
    """Test Shyft API"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': os.getenv('SHYFT_API_KEY')
            }
            url = "https://api.shyft.to/sol/v1/wallet/balance?network=mainnet-beta&wallet=7i5KKsX2weiTkry7jA4ZwSuXGhs5eJBEjY8vVxR4pfRx"
            async with session.get(url, headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    logger.info("✅ Shyft API Connection Successful")
                    return True
                else:
                    logger.error(f"❌ Shyft API Failed: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Shyft API Connection Failed: {str(e)}")
        return False

async def test_bitquery_api():
    """Test Bitquery API"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "X-API-KEY": os.getenv('BITQUERY_API_KEY'),
                "Content-Type": "application/json"
            }
            query = """
            {
                solana {
                    transfers(
                        date: {since: "2024-01-01"}
                    ) {
                        count
                    }
                }
            }
            """
            url = "https://graphql.bitquery.io"
            async with session.post(url, json={"query": query}, headers=headers) as response:
                result = await response.json()
                if "data" in result:
                    logger.info("✅ Bitquery API Connection Successful")
                    return True
                else:
                    logger.error(f"❌ Bitquery API Failed: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Bitquery API Connection Failed: {str(e)}")
        return False

async def test_discord_webhook():
    """Test Discord webhook"""
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        async with aiohttp.ClientSession() as session:
            data = {
                "content": "🔍 API Test Message - Please ignore",
                "username": "API Tester"
            }
            async with session.post(webhook_url, json=data) as response:
                if response.status == 204:
                    logger.info("✅ Discord Webhook Connection Successful")
                    return True
                else:
                    logger.error(f"❌ Discord Webhook Failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Discord Webhook Connection Failed: {str(e)}")
        return False

async def main():
    """Run all tests"""
    logger.info("\n🔄 Starting API Connection Tests...\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {
            "supabase": await test_supabase_connection(),
            "redis": test_redis_connection(),
            "helius": await test_helius_api(),
            "shyft": await test_shyft_api(),
            "bitquery": await test_bitquery_api(),
            "discord": await test_discord_webhook()
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
    with open('connection_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("📝 Results saved to connection_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
