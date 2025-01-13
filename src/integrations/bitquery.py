import aiohttp
import logging
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BitqueryAPI:
    def __init__(self):
        self.api_key = os.getenv("BITQUERY_API_KEY")
        self.base_url = "https://graphql.bitquery.io"
        self.pump_fun_program = os.getenv("PUMP_FUN_PROGRAM_ID")
        
    async def fetch_new_tokens(self) -> List[Dict]:
        """Fetch new token launches from pump.fun"""
        query = """
        query ($network: EthereumNetwork!, $from: ISO8601DateTime, $program: String!) {
          solana(network: $network) {
            programCalls(
              options: {desc: "block.timestamp"}
              date: {since: $from}
              programId: {is: $program}
            ) {
              block {
                timestamp
              }
              transaction {
                signature
              }
              accountData {
                account {
                  address
                }
                program {
                  address
                }
                tokenBalance {
                  tokenAddress
                  tokenSymbol
                  tokenName
                  tokenDecimals
                }
              }
            }
          }
        }
        """
        
        variables = {
            "network": "solana",
            "from": (datetime.now() - timedelta(hours=1)).isoformat(),
            "program": self.pump_fun_program
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json={"query": query, "variables": variables},
                    headers={"X-API-KEY": self.api_key}
                ) as response:
                    data = await response.json()
                    return self._process_token_data(data)
        except Exception as e:
            logger.error(f"Error fetching new tokens: {str(e)}")
            return []
            
    async def fetch_token_trades(self, token_address: str) -> List[Dict]:
        """Fetch DEX trades for a token"""
        query = """
        query ($network: EthereumNetwork!, $token: String!, $from: ISO8601DateTime) {
          solana(network: $network) {
            transfers(
              options: {desc: "block.timestamp"}
              date: {since: $from}
              currency: {is: $token}
            ) {
              block {
                timestamp
              }
              transaction {
                signature
              }
              amount
              currency {
                symbol
                name
                decimals
              }
              sender {
                address
              }
              receiver {
                address
              }
              price {
                usd
              }
            }
          }
        }
        """
        
        variables = {
            "network": "solana",
            "token": token_address,
            "from": (datetime.now() - timedelta(days=1)).isoformat()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json={"query": query, "variables": variables},
                    headers={"X-API-KEY": self.api_key}
                ) as response:
                    data = await response.json()
                    return self._process_trade_data(data)
        except Exception as e:
            logger.error(f"Error fetching token trades: {str(e)}")
            return []
            
    def _process_token_data(self, data: Dict) -> List[Dict]:
        """Process raw token data from Bitquery"""
        try:
            program_calls = data.get("data", {}).get("solana", {}).get("programCalls", [])
            tokens = {}
            
            for call in program_calls:
                account_data = call.get("accountData", {})
                token_balance = account_data.get("tokenBalance", {})
                token_address = token_balance.get("tokenAddress")
                
                if token_address and token_address not in tokens:
                    tokens[token_address] = {
                        "address": token_address,
                        "name": token_balance.get("tokenName"),
                        "symbol": token_balance.get("tokenSymbol"),
                        "decimals": token_balance.get("tokenDecimals"),
                        "deployer": account_data.get("account", {}).get("address"),
                        "created_at": call["block"]["timestamp"]
                    }
                    
            return list(tokens.values())
        except Exception as e:
            logger.error(f"Error processing token data: {str(e)}")
            return []
            
    def _process_trade_data(self, data: Dict) -> List[Dict]:
        """Process raw trade data from Bitquery"""
        try:
            transfers = data.get("data", {}).get("solana", {}).get("transfers", [])
            trades = []
            
            for transfer in transfers:
                trades.append({
                    "timestamp": transfer["block"]["timestamp"],
                    "amount": float(transfer["amount"]),
                    "price": float(transfer.get("price", {}).get("usd", 0)),
                    "seller": transfer["sender"]["address"],
                    "buyer": transfer["receiver"]["address"],
                    "tx_hash": transfer["transaction"]["signature"]
                })
                
            return trades
        except Exception as e:
            logger.error(f"Error processing trade data: {str(e)}")
            return []
