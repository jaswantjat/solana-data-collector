from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

class WalletType(BaseModel):
    is_sniper: bool
    is_insider: bool
    is_whale: bool
    buy_count: int
    sell_count: int
    avg_hold_time: float  # in hours
    total_profit_loss: float
    
class HolderAnalysis(BaseModel):
    total_holders: int
    unique_buyers: int
    unique_sellers: int
    buy_sell_ratio: float
    sniper_count: int
    insider_count: int
    whale_wallets: List[str]
    top_holders: List[str]
    deployer_selling: bool
    risk_score: float
    
    def calculate_risk_score(self) -> float:
        """Calculate risk score based on holder patterns"""
        risk_score = 0
        
        # Check for sniper and insider activity
        if self.sniper_count > 2 or self.insider_count > 2:
            risk_score += 30
            
        # Check buy/sell ratio (over 70% buys is suspicious)
        if self.buy_sell_ratio > 2.33:  # 70/30 = 2.33
            risk_score += 20
            
        # Check whale concentration
        whale_threshold = len(self.whale_wallets)
        if whale_threshold > 2:
            risk_score += whale_threshold * 10
            
        # Check if deployer is selling
        if self.deployer_selling:
            risk_score += 30
            
        return min(100, risk_score)
        
class TopHolderPerformance(BaseModel):
    address: str
    successful_picks: int  # Tokens that went from <$100k to >$1M
    total_picks: int
    profit_loss_30d: float
    win_rate: float
    
    def calculate_confidence_score(self) -> float:
        """Calculate confidence score based on holder's performance"""
        if self.total_picks < 5:
            return 50.0  # Neutral score for new wallets
            
        # Base score on win rate
        base_score = self.win_rate * 100
        
        # Adjust based on recent profit/loss
        profit_modifier = 20 if self.profit_loss_30d > 100000 else \
                        -20 if self.profit_loss_30d < -100000 else 0
                        
        return max(0, min(100, base_score + profit_modifier))
