import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..database.db_manager import DatabaseManager
from ..analysis.analysis_tools import AnalysisTools

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.db = DatabaseManager()
        self.analysis_tools = AnalysisTools()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.reports_dir = self.data_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    async def generate_performance_report(self, token_address: str) -> Dict:
        """Generate comprehensive performance report"""
        try:
            # Get token data
            token_data = await self.analysis_tools._get_token_details(token_address)
            if not token_data:
                return {}
                
            # Calculate performance metrics
            performance = self._calculate_performance_metrics(token_data)
            
            # Generate visualizations
            charts = self._generate_performance_charts(token_data)
            
            # Create report
            report = {
                "token_address": token_address,
                "token_name": token_data["metadata"].get("name", "Unknown"),
                "timestamp": datetime.now().isoformat(),
                "performance_metrics": performance,
                "charts": charts,
                "recommendations": self._generate_recommendations(performance)
            }
            
            # Save report
            self._save_report("performance", token_address, report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {}

    async def generate_risk_report(self, token_address: str) -> Dict:
        """Generate risk assessment report"""
        try:
            # Calculate risk score
            risk_data = await self.analysis_tools.calculate_risk_score(token_address, "token")
            
            # Get additional risk factors
            risk_factors = await self._analyze_risk_factors(token_address)
            
            # Generate visualizations
            charts = self._generate_risk_charts(risk_data, risk_factors)
            
            # Create report
            report = {
                "token_address": token_address,
                "timestamp": datetime.now().isoformat(),
                "risk_score": risk_data["score"],
                "risk_factors": risk_factors,
                "charts": charts,
                "recommendations": self._generate_risk_recommendations(risk_data)
            }
            
            # Save report
            self._save_report("risk", token_address, report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating risk report: {str(e)}")
            return {}

    async def generate_wallet_report(self, wallet_address: str) -> Dict:
        """Generate wallet analysis report"""
        try:
            # Get wallet analysis
            wallet_data = await self.analysis_tools.analyze_wallet(wallet_address)
            
            # Analyze trading patterns
            patterns = self._analyze_trading_patterns(wallet_data)
            
            # Generate visualizations
            charts = self._generate_wallet_charts(wallet_data)
            
            # Create report
            report = {
                "wallet_address": wallet_address,
                "timestamp": datetime.now().isoformat(),
                "wallet_metrics": wallet_data["metrics"],
                "trading_patterns": patterns,
                "risk_assessment": wallet_data.get("risk_score", 1.0),
                "charts": charts,
                "recommendations": self._generate_wallet_recommendations(wallet_data)
            }
            
            # Save report
            self._save_report("wallet", wallet_address, report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating wallet report: {str(e)}")
            return {}

    async def generate_market_report(self) -> Dict:
        """Generate market trend analysis report"""
        try:
            # Get market data
            market_data = await self._get_market_data()
            
            # Analyze trends
            trends = self._analyze_market_trends(market_data)
            
            # Generate visualizations
            charts = self._generate_market_charts(market_data)
            
            # Create report
            report = {
                "timestamp": datetime.now().isoformat(),
                "market_metrics": market_data,
                "trends": trends,
                "charts": charts,
                "recommendations": self._generate_market_recommendations(trends)
            }
            
            # Save report
            self._save_report("market", "trend_analysis", report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating market report: {str(e)}")
            return {}

    def configure_alert(self, config: Dict) -> bool:
        """Configure custom alert settings"""
        try:
            alert_config = {
                "type": config["type"],
                "conditions": config["conditions"],
                "notification": config["notification"],
                "created_at": datetime.now().isoformat()
            }
            
            # Save alert configuration
            alerts_file = self.data_dir / "alert_configs.json"
            
            if alerts_file.exists():
                with open(alerts_file, 'r') as f:
                    alerts = json.load(f)
            else:
                alerts = []
                
            alerts.append(alert_config)
            
            with open(alerts_file, 'w') as f:
                json.dump(alerts, f, indent=2)
                
            return True
            
        except Exception as e:
            logger.error(f"Error configuring alert: {str(e)}")
            return False

    def _calculate_performance_metrics(self, token_data: Dict) -> Dict:
        """Calculate detailed performance metrics"""
        try:
            price_data = token_data.get("price_data", [])
            if not price_data:
                return {}
                
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(price_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Calculate metrics
            metrics = {
                "price_change_24h": self._calculate_change(df, 'price', hours=24),
                "volume_change_24h": self._calculate_change(df, 'volume', hours=24),
                "price_volatility": df['price'].std() / df['price'].mean() if len(df) > 1 else 0,
                "average_volume": df['volume'].mean(),
                "price_momentum": self._calculate_momentum(df),
                "market_cap": float(df.iloc[-1]['price']) * token_data["metadata"].get("total_supply", 0)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {str(e)}")
            return {}

    def _generate_performance_charts(self, token_data: Dict) -> Dict:
        """Generate performance visualization charts"""
        try:
            price_data = token_data.get("price_data", [])
            if not price_data:
                return {}
                
            df = pd.DataFrame(price_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create subplots
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=('Price', 'Volume')
            )
            
            # Add price line
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['price'],
                    name="Price",
                    line=dict(color='#2196f3', width=2)
                ),
                row=1, col=1
            )
            
            # Add volume bars
            fig.add_trace(
                go.Bar(
                    x=df['timestamp'],
                    y=df['volume'],
                    name="Volume",
                    marker_color='rgba(158,158,158,0.2)'
                ),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                height=600,
                showlegend=True,
                title_text="Token Performance Analysis"
            )
            
            return {
                "performance_chart": fig.to_json()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance charts: {str(e)}")
            return {}

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate performance-based recommendations"""
        try:
            recommendations = []
            
            # Price momentum
            if metrics.get("price_momentum", 0) > 0.1:
                recommendations.append("Strong positive price momentum detected. Consider monitoring for potential trend continuation.")
            elif metrics.get("price_momentum", 0) < -0.1:
                recommendations.append("Negative price momentum detected. Consider implementing stop-loss measures.")
                
            # Volume analysis
            if metrics.get("volume_change_24h", 0) > 0.5:
                recommendations.append("Significant volume increase detected. Monitor for potential price movement.")
            elif metrics.get("volume_change_24h", 0) < -0.5:
                recommendations.append("Volume decrease detected. Consider reducing exposure.")
                
            # Volatility
            if metrics.get("price_volatility", 0) > 0.2:
                recommendations.append("High price volatility detected. Consider implementing tight risk management.")
                
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []

    def _save_report(self, report_type: str, identifier: str, report: Dict):
        """Save report to file"""
        try:
            report_dir = self.reports_dir / report_type
            report_dir.mkdir(exist_ok=True)
            
            filename = f"{identifier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_dir / filename, 'w') as f:
                json.dump(report, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")

    def _calculate_change(self, df: pd.DataFrame, column: str, hours: int = 24) -> float:
        """Calculate percentage change over specified time period"""
        try:
            if len(df) < 2:
                return 0
                
            current = df.iloc[-1][column]
            past = df[df['timestamp'] >= df.iloc[-1]['timestamp'] - pd.Timedelta(hours=hours)].iloc[0][column]
            
            return (current - past) / past if past != 0 else 0
            
        except Exception as e:
            logger.error(f"Error calculating change: {str(e)}")
            return 0

    def _calculate_momentum(self, df: pd.DataFrame) -> float:
        """Calculate price momentum indicator"""
        try:
            if len(df) < 2:
                return 0
                
            # Use exponential moving average crossover
            short_ema = df['price'].ewm(span=12, adjust=False).mean()
            long_ema = df['price'].ewm(span=26, adjust=False).mean()
            
            return (short_ema.iloc[-1] - long_ema.iloc[-1]) / long_ema.iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating momentum: {str(e)}")
            return 0
