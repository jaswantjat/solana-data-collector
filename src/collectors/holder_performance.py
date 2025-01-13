import aiohttp
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from ..config import BITQUERY_API_KEY, BITQUERY_ENDPOINT, SHYFT_API_KEY, SHYFT_ENDPOINT

class HolderPerformanceAnalyzer:
    def __init__(self):
        self.bitquery_headers = {
            "X-API-KEY": BITQUERY_API_KEY,
            "Content-Type": "application/json"
        }
        self.shyft_headers = {
            "x-api-key": SHYFT_API_KEY
        }

    async def get_top_holders(self, token_address, exclude_addresses=None):
        """
        Get top 30 holders excluding specified addresses (developer, liquidity pools)
        """
        if exclude_addresses is None:
            exclude_addresses = []

        url = f"{SHYFT_ENDPOINT}/token/holders"
        params = {
            "network": "mainnet-beta",
            "token_address": token_address
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.shyft_headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    holders = data.get('result', [])
                    
                    # Filter out excluded addresses
                    filtered_holders = [
                        holder for holder in holders 
                        if holder['owner'] not in exclude_addresses
                    ]
                    
                    # Sort by balance and get top 30
                    sorted_holders = sorted(
                        filtered_holders,
                        key=lambda x: float(x['balance']),
                        reverse=True
                    )[:30]
                    
                    return sorted_holders
                else:
                    print(f"Error fetching holders: {response.status}")
                    return []

    async def get_wallet_trades(self, wallet_address, days=14):
        """
        Get all trades for a wallet over specified period using Bitquery
        """
        query = """
        {
          solana {
            dexTrades(
              options: {limit: 100}
              date: {since: "%s"}
              address: {is: "%s"}
            ) {
              transaction {
                signature
              }
              block {
                timestamp
              }
              side
              price
              amount: baseAmount
              quote: quoteAmount
              baseCurrency {
                symbol
                address
              }
              quoteCurrency {
                symbol
              }
            }
          }
        }
        """ % ((datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d"), wallet_address)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                BITQUERY_ENDPOINT,
                headers=self.bitquery_headers,
                json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('solana', {}).get('dexTrades', [])
                else:
                    print(f"Error fetching wallet trades: {response.status}")
                    return []

    def calculate_win_rate(self, trades):
        """
        Calculate win rate from trades
        """
        if not trades:
            return {
                'win_rate': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }

        # Group trades by token
        token_trades = {}
        for trade in trades:
            token_address = trade['baseCurrency']['address']
            if token_address not in token_trades:
                token_trades[token_address] = []
            token_trades[token_address].append({
                'timestamp': trade['block']['timestamp'],
                'side': trade['side'],
                'price': float(trade['price']),
                'amount': float(trade['amount']),
                'quote_amount': float(trade['quote'])
            })

        # Calculate PNL for each token
        winning_trades = 0
        total_trades = 0

        for token, token_trade_list in token_trades.items():
            # Sort trades by timestamp
            sorted_trades = sorted(token_trade_list, key=lambda x: x['timestamp'])
            
            # Calculate PNL for completed trade cycles (buy + sell)
            position = 0
            cost_basis = 0
            
            for trade in sorted_trades:
                if trade['side'] == 'BUY':
                    position += trade['amount']
                    cost_basis += trade['quote_amount']
                else:  # SELL
                    if position > 0:
                        # Calculate profit/loss
                        trade_size = min(position, trade['amount'])
                        trade_cost = (cost_basis / position) * trade_size
                        trade_revenue = trade['quote_amount']
                        
                        if trade_revenue > trade_cost:
                            winning_trades += 1
                        
                        total_trades += 1
                        
                        # Update position and cost basis
                        position -= trade_size
                        if position > 0:
                            cost_basis = (cost_basis / position) * trade_size
                        else:
                            cost_basis = 0

        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0

        return {
            'win_rate': win_rate,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades
        }

    async def calculate_pnl(self, wallet_address, days=30):
        """
        Calculate PNL for a wallet over specified period
        """
        trades = await self.get_wallet_trades(wallet_address, days)
        
        if not trades:
            return {
                'total_pnl': 0,
                'total_volume': 0,
                'profitable_tokens': 0,
                'unprofitable_tokens': 0
            }

        # Group trades by token
        token_trades = {}
        for trade in trades:
            token_address = trade['baseCurrency']['address']
            if token_address not in token_trades:
                token_trades[token_address] = []
            token_trades[token_address].append({
                'timestamp': trade['block']['timestamp'],
                'side': trade['side'],
                'price': float(trade['price']),
                'amount': float(trade['amount']),
                'quote_amount': float(trade['quote'])
            })

        total_pnl = 0
        total_volume = 0
        profitable_tokens = 0
        unprofitable_tokens = 0

        for token, token_trade_list in token_trades.items():
            # Sort trades by timestamp
            sorted_trades = sorted(token_trade_list, key=lambda x: x['timestamp'])
            
            # Calculate token PNL
            position = 0
            cost_basis = 0
            token_pnl = 0
            token_volume = 0
            
            for trade in sorted_trades:
                token_volume += trade['quote_amount']
                
                if trade['side'] == 'BUY':
                    position += trade['amount']
                    cost_basis += trade['quote_amount']
                else:  # SELL
                    if position > 0:
                        trade_size = min(position, trade['amount'])
                        trade_cost = (cost_basis / position) * trade_size
                        trade_revenue = trade['quote_amount']
                        
                        token_pnl += trade_revenue - trade_cost
                        
                        position -= trade_size
                        if position > 0:
                            cost_basis = (cost_basis / position) * trade_size
                        else:
                            cost_basis = 0

            total_pnl += token_pnl
            total_volume += token_volume
            
            if token_pnl > 0:
                profitable_tokens += 1
            elif token_pnl < 0:
                unprofitable_tokens += 1

        return {
            'total_pnl': total_pnl,
            'total_volume': total_volume,
            'profitable_tokens': profitable_tokens,
            'unprofitable_tokens': unprofitable_tokens
        }

    async def analyze_holder_performance(self, token_address, exclude_addresses=None):
        """
        Analyze performance of top 30 holders
        """
        # Get top holders
        top_holders = await self.get_top_holders(token_address, exclude_addresses)
        
        holder_performances = []
        
        for holder in top_holders:
            wallet_address = holder['owner']
            
            # Get win rate (14 days)
            trades = await self.get_wallet_trades(wallet_address, days=14)
            win_rate_data = self.calculate_win_rate(trades)
            
            # Get PNL (30 days)
            pnl_data = await self.calculate_pnl(wallet_address, days=30)
            
            holder_performances.append({
                'wallet_address': wallet_address,
                'balance': float(holder['balance']),
                'win_rate': win_rate_data['win_rate'],
                'total_trades': win_rate_data['total_trades'],
                'winning_trades': win_rate_data['winning_trades'],
                'pnl': pnl_data['total_pnl'],
                'volume': pnl_data['total_volume'],
                'profitable_tokens': pnl_data['profitable_tokens']
            })
        
        return holder_performances

    def format_analysis_results(self, token_address, holder_performances):
        """
        Format the holder performance analysis results
        """
        output = []
        output.append(f"\nTop Holder Performance Analysis for {token_address}")
        output.append("-" * 60)

        # Sort holders by PNL
        sorted_holders = sorted(holder_performances, key=lambda x: x['pnl'], reverse=True)

        for idx, holder in enumerate(sorted_holders, 1):
            output.append(f"\n{idx}. Wallet: {holder['wallet_address'][:8]}...")
            output.append(f"   Balance: {holder['balance']:,.2f} tokens")
            output.append(f"   Win Rate (14d): {holder['win_rate']*100:.1f}%")
            output.append(f"   Total Trades: {holder['total_trades']} ({holder['winning_trades']} winning)")
            output.append(f"   PNL (30d): ${holder['pnl']:,.2f}")
            output.append(f"   Volume (30d): ${holder['volume']:,.2f}")
            output.append(f"   Profitable Tokens: {holder['profitable_tokens']}")

        # Calculate aggregate statistics
        avg_win_rate = sum(h['win_rate'] for h in holder_performances) / len(holder_performances) if holder_performances else 0
        total_volume = sum(h['volume'] for h in holder_performances)
        total_pnl = sum(h['pnl'] for h in holder_performances)
        
        output.append("\nAggregate Statistics:")
        output.append(f"Average Win Rate: {avg_win_rate*100:.1f}%")
        output.append(f"Total Trading Volume: ${total_volume:,.2f}")
        output.append(f"Total PNL: ${total_pnl:,.2f}")

        return "\n".join(output)
