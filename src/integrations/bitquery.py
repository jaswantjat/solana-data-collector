import aiohttp
import logging
from typing import Dict, List, Optional, Any
import os
from datetime import datetime, timedelta
import json

from ..error_handling.api_errors import (
    APIError,
    APIKeyError,
    handle_api_error,
    should_retry
)
from ..test.mock_data import should_use_mock_data, get_mock_token

logger = logging.getLogger(__name__)

class BitqueryAPI:
    def __init__(self):
        self.api_key = os.getenv("BITQUERY_API_KEY")
        if not self.api_key:
            raise APIKeyError("Bitquery")
            
        self.base_url = "https://graphql.bitquery.io"
        self.session = None
        self.max_retries = 3
        self.use_mock = should_use_mock_data()
        
    async def initialize(self):
        """Initialize Bitquery API session"""
        if not self.session and not self.use_mock:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Close Bitquery API session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    def _sanitize_query_vars(self, variables: Dict) -> Dict:
        """Sanitize GraphQL variables for serialization"""
        sanitized = {}
        for key, value in variables.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, (list, dict)):
                sanitized[key] = json.dumps(value)
            elif isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            else:
                sanitized[key] = str(value)
        return sanitized
            
    async def _execute_query(
        self,
        query: str,
        variables: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict:
        """Execute a GraphQL query with retries and error handling"""
        if not self.session and not self.use_mock:
            await self.initialize()
            
        try:
            sanitized_vars = self._sanitize_query_vars(variables or {})
            async with self.session.post(
                self.base_url,
                json={
                    "query": query,
                    "variables": sanitized_vars
                },
                headers={"X-API-KEY": self.api_key}
            ) as response:
                data = await response.json()
                
                if response.status != 200:
                    error = handle_api_error(
                        Exception(str(data.get("errors", ["Unknown error"]))),
                        "Bitquery",
                        "GraphQL",
                        response.status,
                        data
                    )
                    
                    if should_retry(error, retry_count, self.max_retries):
                        return await self._execute_query(
                            query,
                            variables,
                            retry_count + 1
                        )
                    raise error
                    
                if "errors" in data:
                    error = handle_api_error(
                        Exception(str(data["errors"])),
                        "Bitquery",
                        "GraphQL",
                        response.status,
                        data
                    )
                    
                    if should_retry(error, retry_count, self.max_retries):
                        return await self._execute_query(
                            query,
                            variables,
                            retry_count + 1
                        )
                    raise error
                    
                return data.get("data", {})
                
        except Exception as e:
            error = handle_api_error(e, "Bitquery", "GraphQL")
            if should_retry(error, retry_count, self.max_retries):
                return await self._execute_query(
                    query,
                    variables,
                    retry_count + 1
                )
            raise error
            
    async def fetch_new_tokens(self) -> List[Dict]:
        """Fetch new token launches"""
        if self.use_mock:
            mock_token = get_mock_token()
            mock_token["launch_time"] = datetime.now().isoformat()
            return [mock_token]
            
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
            "program": os.getenv("PUMP_FUN_PROGRAM_ID")
        }
        
        try:
            data = await self._execute_query(query, variables)
            return self._process_token_data(data)
        except APIError as e:
            logger.error(f"API error fetching new tokens: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching new tokens: {str(e)}")
            return []
            
    async def fetch_token_trades(self, token_address: str) -> List[Dict]:
        """Fetch DEX trades for a token"""
        if self.use_mock:
            return []
            
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
            data = await self._execute_query(query, variables)
            return self._process_trade_data(data)
        except APIError as e:
            logger.error(f"API error fetching token trades: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching token trades: {str(e)}")
            return []
            
    async def get_token_volume(self, token_address: str, days: int = 30) -> Dict:
        """Get token trading volume data"""
        if self.use_mock:
            return {
                "total_volume_usd": 0,
                "daily_volumes": []
            }
            
        try:
            query = """
            query ($token: String!, $since: ISO8601DateTime) {
                solana {
                    transfers(
                        options: {limit: 100}
                        date: {since: $since}
                        currency: {is: $token}
                    ) {
                        amount
                        count
                        volumeUSD: amount(calculate: sum, in: USD)
                        date {
                            date
                        }
                    }
                }
            }
            """
            
            variables = {
                "token": token_address,
                "since": (datetime.now() - timedelta(days=days)).isoformat()
            }
            
            data = await self._execute_query(query, variables)
            
            return self._process_volume_data(data)
            
        except APIError as e:
            logger.error(f"API error fetching token volume: {str(e)}")
            return {
                "total_volume_usd": 0,
                "daily_volumes": []
            }
        except Exception as e:
            logger.error(f"Error fetching token volume: {str(e)}")
            return {
                "total_volume_usd": 0,
                "daily_volumes": []
            }
            
    def _process_token_data(self, data: Dict) -> List[Dict]:
        """Process raw token data from Bitquery"""
        try:
            program_calls = data.get("solana", {}).get("programCalls", [])
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
            transfers = data.get("solana", {}).get("transfers", [])
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
            
    def _process_volume_data(self, data: Dict) -> Dict:
        """Process volume data from Bitquery"""
        try:
            transfers = data.get("solana", {}).get("transfers", [])
            
            daily_volumes = []
            total_volume_usd = 0
            
            for transfer in transfers:
                volume_usd = float(transfer.get("volumeUSD", 0))
                date = transfer.get("date", {}).get("date")
                
                if date and volume_usd > 0:
                    daily_volumes.append({
                        "date": date,
                        "volume_usd": volume_usd,
                        "transaction_count": int(transfer.get("count", 0))
                    })
                    total_volume_usd += volume_usd
                    
            return {
                "total_volume_usd": total_volume_usd,
                "daily_volumes": sorted(daily_volumes, key=lambda x: x["date"])
            }
            
        except Exception as e:
            logger.error(f"Error processing volume data: {str(e)}")
            return {
                "total_volume_usd": 0,
                "daily_volumes": []
            }
