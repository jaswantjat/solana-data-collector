import aiohttp
import asyncio
from ..config import SHYFT_API_KEY, HELIUS_API_KEY, SHYFT_ENDPOINT, HELIUS_ENDPOINT

class WalletAnalyzer:
    def __init__(self):
        self.shyft_headers = {
            "x-api-key": SHYFT_API_KEY
        }
        self.helius_headers = {
            "Authorization": f"Bearer {HELIUS_API_KEY}"
        }

    async def get_wallet_portfolio(self, wallet_address):
        """
        Get wallet portfolio using SHYFT API
        """
        url = f"{SHYFT_ENDPOINT}/wallet/portfolio"
        params = {
            "network": "mainnet-beta",
            "wallet": wallet_address
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.shyft_headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error fetching wallet portfolio: {response.status}")
                    return None

    async def get_transaction_history(self, wallet_address):
        """
        Get transaction history using Helius API
        """
        url = f"{HELIUS_ENDPOINT}/addresses/{wallet_address}/transactions"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.helius_headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error fetching transaction history: {response.status}")
                    return None

    async def get_nft_holdings(self, wallet_address):
        """
        Get NFT holdings using SHYFT API
        """
        url = f"{SHYFT_ENDPOINT}/wallet/nfts"
        params = {
            "network": "mainnet-beta",
            "wallet": wallet_address
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.shyft_headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error fetching NFT holdings: {response.status}")
                    return None

    async def analyze_wallet(self, wallet_address):
        """
        Comprehensive wallet analysis combining all data points
        """
        portfolio = await self.get_wallet_portfolio(wallet_address)
        transactions = await self.get_transaction_history(wallet_address)
        nfts = await self.get_nft_holdings(wallet_address)

        return {
            "portfolio": portfolio,
            "transactions": transactions,
            "nfts": nfts
        }
