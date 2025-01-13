from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

class TwitterAccount(BaseModel):
    handle: str
    name_changes: List[Dict[str, datetime]]
    follower_count: int
    engagement_rate: float
    is_verified: bool
    creation_date: datetime
    
class TwitterMention(BaseModel):
    tweet_id: str
    author: str
    is_influencer: bool
    sentiment_score: float  # -1 to 1
    engagement: Dict[str, int]  # likes, retweets, replies
    timestamp: datetime
    
class TwitterAnalysis(BaseModel):
    token_account: Optional[TwitterAccount]
    mentions: List[TwitterMention]
    total_mentions: int
    average_sentiment: float
    influencer_mentions: int
    name_change_count: int
    risk_score: float
    
    def calculate_risk_score(self) -> float:
        """Calculate risk score based on Twitter activity"""
        risk_score = 0
        
        # Check for frequent name changes (suspicious behavior)
        if self.token_account:
            if self.name_change_count > 3:
                risk_score += 30
                
            # New account with high activity is suspicious
            account_age = (datetime.now() - self.token_account.creation_date).days
            if account_age < 30 and self.total_mentions > 1000:
                risk_score += 20
                
        # Check sentiment
        if self.average_sentiment < -0.2:
            risk_score += 25
            
        # Low influencer engagement despite high mentions is suspicious
        if self.total_mentions > 500 and self.influencer_mentions < 3:
            risk_score += 15
            
        return min(100, risk_score)
