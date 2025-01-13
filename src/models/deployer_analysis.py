from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

class TokenHistory(BaseModel):
    address: str
    launch_date: datetime
    max_market_cap: float
    current_market_cap: float
    is_successful: bool  # True if reached $3M market cap

class DeployerAnalysis(BaseModel):
    address: str
    total_tokens_launched: int
    successful_tokens: List[TokenHistory]
    failed_tokens: List[TokenHistory]
    success_rate: float
    is_blacklisted: bool
    last_token_launch: Optional[datetime]
    risk_score: float  # 0-100, higher is riskier
    
    def calculate_risk_score(self) -> float:
        """Calculate risk score based on deployer history"""
        if self.is_blacklisted:
            return 100.0
            
        if self.total_tokens_launched == 0:
            return 50.0  # Neutral score for new deployers
            
        # Calculate percentage of failed tokens that never reached $200k
        total_failed = len(self.failed_tokens)
        never_reached_threshold = sum(
            1 for token in self.failed_tokens 
            if token.max_market_cap < 200000
        )
        
        failure_rate = never_reached_threshold / total_failed if total_failed > 0 else 0
        
        # If 97% or more tokens failed to reach $200k, high risk
        if failure_rate >= 0.97:
            return 90.0
            
        # Consider success rate and recent performance
        base_score = 100 - (self.success_rate * 100)
        
        # Adjust based on recent performance (last 3 tokens)
        recent_tokens = sorted(
            self.successful_tokens + self.failed_tokens,
            key=lambda x: x.launch_date,
            reverse=True
        )[:3]
        
        recent_success = sum(1 for token in recent_tokens if token.is_successful)
        recent_modifier = -20 if recent_success >= 2 else 20 if recent_success == 0 else 0
        
        return max(0, min(100, base_score + recent_modifier))
