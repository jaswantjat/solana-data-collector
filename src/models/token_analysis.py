from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

class TokenAnalysis(BaseModel):
    token_address: str
    name: Optional[str]
    symbol: Optional[str]
    market_cap: float
    price: float
    price_change_24h: float
    confidence_score: float
    deployer_analysis: Dict
    holder_analysis: Dict
    twitter_analysis: Dict
    top_holder_analysis: Dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        arbitrary_types_allowed = True
