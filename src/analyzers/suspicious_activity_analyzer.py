"""Module for analyzing suspicious activity in token trading and transfers."""
import asyncio
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

class SuspiciousActivityAnalyzer:
    def __init__(self):
        self.volume_threshold = 0.7  # 70% of volume from single source is suspicious
        self.supply_threshold = 0.9  # 90% of supply in single wallet is suspicious
        self.batch_time_threshold = 300  # 5 minutes between batches is suspicious
        self.similar_amount_threshold = 0.05  # 5% difference for similar amounts
    
    async def analyze_token(
        self,
        token_data: Dict,
        trade_data: Dict,
        include_holder_analysis: bool = True,
        include_twitter_analysis: bool = True
    ) -> Dict:
        """
        Analyze a token for suspicious activity.
        
        Args:
            token_data: Token metadata and info
            trade_data: Trading history and metrics
            include_holder_analysis: Whether to analyze holder distribution
            include_twitter_analysis: Whether to analyze social media activity
            
        Returns:
            Dict containing analysis results and risk assessment
        """
        result = {
            'is_suspicious': False,
            'risk_score': 0,
            'warnings': [],
            'metrics': {}
        }

        try:
            # Basic token checks
            if not token_data or not trade_data:
                result['warnings'].append("Insufficient data for complete analysis")
                result['risk_score'] = 0.5  # Medium risk due to lack of data
                return result

            # Analyze trading patterns
            trades = trade_data.get('trades', [])
            volume_analysis = await self.analyze_volume_patterns(trades)
            
            if volume_analysis['is_suspicious']:
                result['is_suspicious'] = True
                result['warnings'].extend(volume_analysis['reasons'])
                result['metrics'].update(volume_analysis['metrics'])
                result['risk_score'] += 0.3

            # Analyze token supply if holder analysis is requested
            if include_holder_analysis:
                initial_transfers = trade_data.get('initial_transfers', [])
                current_holders = trade_data.get('current_holders', [])
                
                supply_analysis = await self.analyze_supply_distribution(
                    initial_transfers, current_holders
                )
                
                if supply_analysis['is_suspicious']:
                    result['is_suspicious'] = True
                    result['warnings'].extend(supply_analysis['reasons'])
                    result['metrics'].update(supply_analysis['metrics'])
                    result['risk_score'] += 0.3

            # Analyze market metrics
            total_supply = float(token_data.get('total_supply', 0))
            price = float(trade_data.get('latest_price', 0))
            volume_24h = float(trade_data.get('total_volume', 0))
            
            market_analysis = await self.get_market_cap_analysis(
                total_supply, price, volume_24h
            )
            
            if market_analysis['is_suspicious']:
                result['is_suspicious'] = True
                result['warnings'].extend(market_analysis['reasons'])
                result['metrics'].update(market_analysis['metrics'])
                result['risk_score'] += 0.2

            # Add social media analysis if requested
            if include_twitter_analysis and 'social' in token_data:
                social_data = token_data['social']
                # Add social media analysis logic here
                pass

            # Cap risk score at 1.0
            result['risk_score'] = min(result['risk_score'], 1.0)

            # Add recommendations based on findings
            result['recommendations'] = self._generate_recommendations(result)

        except Exception as e:
            result['warnings'].append(f"Error during analysis: {str(e)}")
            result['risk_score'] = 0.7  # High risk due to analysis error

        return result

    def _generate_recommendations(self, analysis_result: Dict) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        if analysis_result['is_suspicious']:
            if any('volume' in warning.lower() for warning in analysis_result['warnings']):
                recommendations.append(
                    "Exercise caution: Suspicious trading volume patterns detected"
                )
            
            if any('supply' in warning.lower() for warning in analysis_result['warnings']):
                recommendations.append(
                    "Be aware: Token supply is highly concentrated"
                )
            
            if any('market' in warning.lower() for warning in analysis_result['warnings']):
                recommendations.append(
                    "Warning: Unusual market metrics detected"
                )
            
            if analysis_result['risk_score'] > 0.7:
                recommendations.append(
                    "High Risk: Multiple suspicious patterns detected. "
                    "Thorough due diligence recommended"
                )
        else:
            recommendations.append(
                "No major suspicious patterns detected. Always conduct your own research"
            )
            
        return recommendations
        
    async def analyze_volume_patterns(self, trades: List[Dict]) -> Dict:
        """
        Analyze trading volume patterns to detect fake volume
        """
        result = {
            'is_suspicious': False,
            'reasons': [],
            'metrics': {}
        }
        
        if not trades:
            return result
            
        # Group trades by wallet
        wallet_volumes = defaultdict(float)
        total_volume = 0
        
        for trade in trades:
            wallet = trade['wallet']
            volume = float(trade['amount']) * float(trade['price'])
            wallet_volumes[wallet] += volume
            total_volume += volume
            
        if total_volume == 0:
            return result
            
        # Check for concentrated volume
        max_wallet_volume = max(wallet_volumes.values())
        max_volume_ratio = max_wallet_volume / total_volume
        
        result['metrics']['total_volume'] = total_volume
        result['metrics']['max_wallet_volume_ratio'] = max_volume_ratio
        
        if max_volume_ratio > self.volume_threshold:
            result['is_suspicious'] = True
            result['reasons'].append(
                f"Single wallet responsible for {max_volume_ratio:.1%} of total volume"
            )
            
        # Check for wash trading patterns
        wash_trades = self._detect_wash_trades(trades)
        if wash_trades:
            result['is_suspicious'] = True
            result['reasons'].append(
                f"Detected {len(wash_trades)} potential wash trading patterns"
            )
            result['metrics']['wash_trade_count'] = len(wash_trades)
            
        return result
        
    def _detect_wash_trades(self, trades: List[Dict]) -> List[Dict]:
        """
        Detect potential wash trading patterns
        """
        wash_trades = []
        wallet_trades = defaultdict(list)
        
        # Group trades by wallet
        for trade in trades:
            wallet_trades[trade['wallet']].append(trade)
            
        for wallet, wallet_trade_list in wallet_trades.items():
            # Sort trades by timestamp
            sorted_trades = sorted(wallet_trade_list, key=lambda x: x['timestamp'])
            
            # Look for alternating buy/sell patterns with similar amounts
            for i in range(len(sorted_trades) - 1):
                current_trade = sorted_trades[i]
                next_trade = sorted_trades[i + 1]
                
                # Check if trades are opposite directions
                if current_trade['side'] != next_trade['side']:
                    # Check if amounts are similar
                    amount_diff = abs(
                        float(current_trade['amount']) - float(next_trade['amount'])
                    ) / float(current_trade['amount'])
                    
                    if amount_diff <= self.similar_amount_threshold:
                        wash_trades.append({
                            'trade1': current_trade,
                            'trade2': next_trade,
                            'amount_difference': amount_diff
                        })
                        
        return wash_trades
        
    async def analyze_supply_distribution(
        self,
        initial_transfers: List[Dict],
        current_holders: List[Dict]
    ) -> Dict:
        """
        Analyze token supply distribution for suspicious patterns
        """
        result = {
            'is_suspicious': False,
            'reasons': [],
            'metrics': {}
        }
        
        # Analyze initial supply distribution
        initial_supply_analysis = self._analyze_initial_supply(initial_transfers)
        if initial_supply_analysis['is_suspicious']:
            result['is_suspicious'] = True
            result['reasons'].extend(initial_supply_analysis['reasons'])
            result['metrics'].update(initial_supply_analysis['metrics'])
            
        # Analyze current holder distribution
        current_supply_analysis = self._analyze_current_supply(current_holders)
        if current_supply_analysis['is_suspicious']:
            result['is_suspicious'] = True
            result['reasons'].extend(current_supply_analysis['reasons'])
            result['metrics'].update(current_supply_analysis['metrics'])
            
        return result
        
    def _analyze_initial_supply(self, transfers: List[Dict]) -> Dict:
        """
        Analyze initial token supply distribution
        """
        result = {
            'is_suspicious': False,
            'reasons': [],
            'metrics': {}
        }
        
        if not transfers:
            return result
            
        # Sort transfers by timestamp
        sorted_transfers = sorted(transfers, key=lambda x: x['timestamp'])
        
        # Check for suspicious batch transfers
        batches = self._identify_transfer_batches(sorted_transfers)
        if len(batches) > 1:
            suspicious_batches = self._analyze_batch_patterns(batches)
            if suspicious_batches:
                result['is_suspicious'] = True
                result['reasons'].append(
                    f"Detected {len(suspicious_batches)} suspicious transfer batches"
                )
                result['metrics']['suspicious_batch_count'] = len(suspicious_batches)
                
        # Check for single entity control
        wallet_amounts = defaultdict(float)
        total_supply = 0
        
        for transfer in transfers:
            wallet = transfer['to_address']
            amount = float(transfer['amount'])
            wallet_amounts[wallet] += amount
            total_supply += amount
            
        if total_supply > 0:
            max_wallet_amount = max(wallet_amounts.values())
            max_supply_ratio = max_wallet_amount / total_supply
            
            result['metrics']['max_wallet_supply_ratio'] = max_supply_ratio
            
            if max_supply_ratio > self.supply_threshold:
                result['is_suspicious'] = True
                result['reasons'].append(
                    f"Single wallet controls {max_supply_ratio:.1%} of initial supply"
                )
                
        return result
        
    def _identify_transfer_batches(self, transfers: List[Dict]) -> List[List[Dict]]:
        """
        Group transfers into batches based on timing
        """
        batches = []
        current_batch = []
        
        for transfer in transfers:
            if not current_batch:
                current_batch.append(transfer)
                continue
                
            time_diff = (
                transfer['timestamp'] - current_batch[-1]['timestamp']
            ).total_seconds()
            
            if time_diff <= self.batch_time_threshold:
                current_batch.append(transfer)
            else:
                batches.append(current_batch)
                current_batch = [transfer]
                
        if current_batch:
            batches.append(current_batch)
            
        return batches
        
    def _analyze_batch_patterns(self, batches: List[List[Dict]]) -> List[Dict]:
        """
        Analyze transfer batches for suspicious patterns
        """
        suspicious_batches = []
        
        for i, batch in enumerate(batches):
            batch_analysis = {
                'batch_index': i,
                'suspicious_patterns': []
            }
            
            # Check for similar amounts in batch
            amounts = [float(t['amount']) for t in batch]
            amount_std = np.std(amounts)
            amount_mean = np.mean(amounts)
            
            if amount_std / amount_mean < self.similar_amount_threshold:
                batch_analysis['suspicious_patterns'].append(
                    "Uniform distribution of amounts"
                )
                
            # Check for sequential wallet patterns
            wallets = [t['to_address'] for t in batch]
            if len(set(wallets)) == len(wallets) and len(wallets) > 5:
                batch_analysis['suspicious_patterns'].append(
                    "Sequential different wallets"
                )
                
            if batch_analysis['suspicious_patterns']:
                suspicious_batches.append(batch_analysis)
                
        return suspicious_batches
        
    def _analyze_current_supply(self, holders: List[Dict]) -> Dict:
        """
        Analyze current token supply distribution
        """
        result = {
            'is_suspicious': False,
            'reasons': [],
            'metrics': {}
        }
        
        if not holders:
            return result
            
        total_supply = sum(float(h['balance']) for h in holders)
        
        if total_supply > 0:
            # Calculate Gini coefficient for supply distribution
            gini = self._calculate_gini_coefficient(
                [float(h['balance']) for h in holders]
            )
            result['metrics']['gini_coefficient'] = gini
            
            if gini > 0.9:  # Extremely unequal distribution
                result['is_suspicious'] = True
                result['reasons'].append(
                    f"Highly concentrated supply distribution (Gini: {gini:.2f})"
                )
                
            # Check for suspicious holder patterns
            max_balance = max(float(h['balance']) for h in holders)
            max_supply_ratio = max_balance / total_supply
            
            result['metrics']['max_holder_supply_ratio'] = max_supply_ratio
            
            if max_supply_ratio > self.supply_threshold:
                result['is_suspicious'] = True
                result['reasons'].append(
                    f"Single holder controls {max_supply_ratio:.1%} of current supply"
                )
                
        return result
        
    def _calculate_gini_coefficient(self, values: List[float]) -> float:
        """
        Calculate Gini coefficient for measuring inequality
        """
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n == 0:
            return 0
            
        index = np.arange(1, n + 1)
        return (
            (2 * np.sum(index * sorted_values)) / (n * np.sum(sorted_values))
        ) - ((n + 1) / n)
        
    async def get_market_cap_analysis(
        self,
        total_supply: float,
        price: float,
        volume_24h: float
    ) -> Dict:
        """
        Analyze market cap and related metrics for suspicious patterns
        """
        result = {
            'is_suspicious': False,
            'reasons': [],
            'metrics': {}
        }
        
        market_cap = total_supply * price
        
        # Calculate volume/market cap ratio
        if market_cap > 0:
            volume_market_cap_ratio = volume_24h / market_cap
            result['metrics']['volume_market_cap_ratio'] = volume_market_cap_ratio
            
            # Suspiciously high trading volume relative to market cap
            if volume_market_cap_ratio > 0.5:  # More than 50% of market cap traded in 24h
                result['is_suspicious'] = True
                result['reasons'].append(
                    f"Unusually high trading volume ({volume_market_cap_ratio:.1%} of market cap)"
                )
                
        # Store basic metrics
        result['metrics'].update({
            'market_cap': market_cap,
            'total_supply': total_supply,
            'price': price,
            'volume_24h': volume_24h
        })
        
        return result
