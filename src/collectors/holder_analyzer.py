import aiohttp
import asyncio
from datetime import datetime
import json
from ..config import SHYFT_API_KEY, SHYFT_ENDPOINT

class HolderAnalyzer:
    def __init__(self):
        self.headers = {
            "x-api-key": SHYFT_API_KEY
        }
        # Load known addresses from JSON file
        self.known_addresses = self.load_known_addresses()

    def load_known_addresses(self):
        """
        Load known sniper and insider wallet addresses from JSON file
        """
        try:
            with open('data/known_addresses.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'snipers': [],
                'insiders': []
            }

    async def get_token_holders(self, token_address):
        """
        Get total number of holders and holder distribution using Solscan API
        """
        url = f"{SHYFT_ENDPOINT}/token/holders"
        params = {
            "network": "mainnet-beta",
            "token_address": token_address
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'total_holders': len(data.get('result', [])),
                        'holders': data.get('result', [])
                    }
                else:
                    print(f"Error fetching holder data: {response.status}")
                    return {'total_holders': 0, 'holders': []}

    async def analyze_deployer_transactions(self, token_address, deployer_address):
        """
        Analyze deployer's token transactions to identify sales
        """
        url = f"{SHYFT_ENDPOINT}/wallet/transactions"
        params = {
            "network": "mainnet-beta",
            "wallet": deployer_address,
            "token_address": token_address
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    transactions = data.get('result', [])
                    
                    sales = []
                    total_sold = 0
                    
                    for tx in transactions:
                        if tx['type'] == 'TRANSFER' and tx['from_address'] == deployer_address:
                            sales.append({
                                'timestamp': tx['timestamp'],
                                'amount': float(tx['amount']),
                                'to_address': tx['to_address']
                            })
                            total_sold += float(tx['amount'])
                    
                    return {
                        'total_sales': len(sales),
                        'total_amount_sold': total_sold,
                        'sales_details': sales
                    }
                else:
                    print(f"Error fetching deployer transactions: {response.status}")
                    return {'total_sales': 0, 'total_amount_sold': 0, 'sales_details': []}

    async def identify_sniper_purchases(self, token_address):
        """
        Identify purchases from known sniper wallets
        """
        url = f"{SHYFT_ENDPOINT}/token/transfers"
        params = {
            "network": "mainnet-beta",
            "token_address": token_address
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    transfers = data.get('result', [])
                    
                    sniper_purchases = []
                    insider_purchases = []
                    
                    for transfer in transfers:
                        buyer = transfer['to_address']
                        if buyer in self.known_addresses['snipers']:
                            sniper_purchases.append({
                                'wallet': buyer,
                                'amount': float(transfer['amount']),
                                'timestamp': transfer['timestamp']
                            })
                        elif buyer in self.known_addresses['insiders']:
                            insider_purchases.append({
                                'wallet': buyer,
                                'amount': float(transfer['amount']),
                                'timestamp': transfer['timestamp']
                            })
                    
                    return {
                        'sniper_count': len(set(p['wallet'] for p in sniper_purchases)),
                        'insider_count': len(set(p['wallet'] for p in insider_purchases)),
                        'sniper_purchases': sniper_purchases,
                        'insider_purchases': insider_purchases
                    }
                else:
                    print(f"Error fetching transfer data: {response.status}")
                    return {
                        'sniper_count': 0,
                        'insider_count': 0,
                        'sniper_purchases': [],
                        'insider_purchases': []
                    }

    def format_analysis_results(self, token_address, holder_data, deployer_data, sniper_data):
        """
        Format the analysis results for better readability
        """
        output = []
        output.append(f"\nToken Analysis Report for {token_address}")
        output.append("-" * 50)
        
        # Holder Information
        output.append(f"\nHolder Information:")
        output.append(f"Total Holders: {holder_data['total_holders']}")
        
        # Deployer Activity
        output.append(f"\nDeployer Activity:")
        output.append(f"Total Sales: {deployer_data['total_sales']}")
        output.append(f"Total Amount Sold: {deployer_data['total_amount_sold']:,.2f} tokens")
        
        if deployer_data['sales_details']:
            output.append("\nRecent Sales:")
            for sale in deployer_data['sales_details'][-5:]:  # Show last 5 sales
                output.append(f"- {sale['amount']:,.2f} tokens sold at {sale['timestamp']}")
        
        # Sniper/Insider Activity
        output.append(f"\nSuspicious Activity:")
        output.append(f"Known Sniper Wallets Involved: {sniper_data['sniper_count']}")
        output.append(f"Known Insider Wallets Involved: {sniper_data['insider_count']}")
        
        if sniper_data['sniper_purchases']:
            output.append("\nSniper Purchases:")
            for purchase in sniper_data['sniper_purchases'][-5:]:  # Show last 5 purchases
                output.append(f"- {purchase['amount']:,.2f} tokens bought by {purchase['wallet'][:8]}...")
        
        if sniper_data['insider_purchases']:
            output.append("\nInsider Purchases:")
            for purchase in sniper_data['insider_purchases'][-5:]:  # Show last 5 purchases
                output.append(f"- {purchase['amount']:,.2f} tokens bought by {purchase['wallet'][:8]}...")
        
        return "\n".join(output)
