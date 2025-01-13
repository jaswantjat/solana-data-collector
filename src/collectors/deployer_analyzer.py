import aiohttp
import asyncio
from datetime import datetime, timedelta
from ..config import BITQUERY_API_KEY, BITQUERY_ENDPOINT

class DeployerAnalyzer:
    def __init__(self):
        self.headers = {
            "X-API-KEY": BITQUERY_API_KEY,
            "Content-Type": "application/json"
        }

    async def get_deployed_tokens(self, deployer_address):
        """
        Get all tokens deployed by a specific address
        """
        query = """
        {
          solana {
            transfers(
              options: {limit: 100}
              date: {since: "2024-01-12"}
              sender: {is: "%s"}
              transferType: {is: mint}
            ) {
              block {
                timestamp
                height
              }
              transaction {
                signature
              }
              currency {
                address
                name
                symbol
              }
              amount
              receiver
            }
          }
        }
        """ % deployer_address

        async with aiohttp.ClientSession() as session:
            async with session.post(
                BITQUERY_ENDPOINT,
                headers=self.headers,
                json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('solana', {}).get('transfers', [])
                else:
                    print(f"Error fetching deployed tokens: {response.status}")
                    return []

    async def get_token_market_cap(self, token_address):
        """
        Calculate market cap for a specific token
        """
        query = """
        {
          solana {
            dexTrades(
              options: {limit: 1, desc: "block.timestamp"}
              baseCurrency: {is: "%s"}
            ) {
              block {
                timestamp
              }
              price
              baseCurrency {
                totalSupply
              }
            }
          }
        }
        """ % token_address

        async with aiohttp.ClientSession() as session:
            async with session.post(
                BITQUERY_ENDPOINT,
                headers=self.headers,
                json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    trades = data.get('data', {}).get('solana', {}).get('dexTrades', [])
                    if trades:
                        trade = trades[0]
                        price = float(trade['price'])
                        total_supply = float(trade['baseCurrency']['totalSupply'])
                        market_cap = price * total_supply
                        return market_cap
                return 0

    async def analyze_deployer_history(self, deployer_address):
        """
        Analyze deployer's history and success rate
        """
        deployed_tokens = await self.get_deployed_tokens(deployer_address)
        
        successful_tokens = 0
        total_tokens = len(deployed_tokens)
        token_details = []

        for token in deployed_tokens:
            token_address = token['currency']['address']
            market_cap = await self.get_token_market_cap(token_address)
            
            token_info = {
                'address': token_address,
                'name': token['currency']['name'],
                'symbol': token['currency']['symbol'],
                'deployment_time': token['block']['timestamp'],
                'market_cap': market_cap
            }
            
            if market_cap >= 3_000_000:  # 3 million market cap threshold
                successful_tokens += 1
            
            token_details.append(token_info)

        return {
            'total_tokens': total_tokens,
            'successful_tokens': successful_tokens,
            'success_rate': (successful_tokens / total_tokens) if total_tokens > 0 else 0,
            'token_details': token_details
        }

    def format_analysis_results(self, results):
        """
        Format the analysis results for better readability
        """
        output = []
        output.append(f"Deployer Analysis Summary:")
        output.append(f"Total Tokens Deployed: {results['total_tokens']}")
        output.append(f"Tokens reaching 3M+ market cap: {results['successful_tokens']}")
        output.append(f"Success Rate: {results['success_rate']*100:.2f}%")
        output.append("\nToken Details:")
        
        for token in results['token_details']:
            output.append(f"\nToken: {token['name']} ({token['symbol']})")
            output.append(f"Address: {token['address']}")
            output.append(f"Deployment Time: {token['deployment_time']}")
            output.append(f"Current Market Cap: ${token['market_cap']:,.2f}")
        
        return "\n".join(output)
