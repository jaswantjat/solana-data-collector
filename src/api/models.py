"""API models for request and response validation."""
from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from decimal import Decimal

class TokenInfo(BaseModel):
    """Token information model."""
    address: str = Field(..., description="Token address")
    symbol: Optional[str] = Field(None, description="Token symbol")
    name: Optional[str] = Field(None, description="Token name")
    decimals: Optional[int] = Field(None, description="Token decimals")

class PriceInfo(BaseModel):
    """Price information model."""
    price: Decimal = Field(..., description="Current price")
    price_change_24h: Optional[Decimal] = Field(None, description="24h price change percentage")
    volume_24h: Optional[Decimal] = Field(None, description="24h trading volume")
    market_cap: Optional[Decimal] = Field(None, description="Market capitalization")

class TokenAnalysisRequest(BaseModel):
    """Token analysis request model."""
    token_address: str = Field(..., description="Token address to analyze")
    include_price_history: bool = Field(False, description="Include price history in response")
    time_range: Optional[str] = Field(None, description="Time range for analysis (e.g., '1d', '7d', '30d')")

    @validator('token_address')
    def validate_token_address(cls, v):
        """Validate token address format."""
        if not v or len(v) != 44:  # Solana addresses are 44 characters
            raise ValueError("Invalid Solana token address")
        return v

class TokenAnalysisResponse(BaseModel):
    """Token analysis response model."""
    token: TokenInfo
    price_info: PriceInfo
    holders_count: Optional[int] = Field(None, description="Number of token holders")
    price_history: Optional[List[Dict[str, Union[datetime, Decimal]]]] = Field(
        None, description="Historical price data"
    )
    risk_metrics: Optional[Dict[str, Union[str, float]]] = Field(
        None, description="Risk assessment metrics"
    )

class WalletAnalysisRequest(BaseModel):
    """Wallet analysis request model."""
    wallet_address: str = Field(..., description="Wallet address to analyze")
    include_transaction_history: bool = Field(False, description="Include transaction history")
    time_range: Optional[str] = Field(None, description="Time range for analysis")

    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        """Validate wallet address format."""
        if not v or len(v) != 44:  # Solana addresses are 44 characters
            raise ValueError("Invalid Solana wallet address")
        return v

class TransactionInfo(BaseModel):
    """Transaction information model."""
    signature: str = Field(..., description="Transaction signature")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    type: str = Field(..., description="Transaction type")
    amount: Optional[Decimal] = Field(None, description="Transaction amount")
    token_address: Optional[str] = Field(None, description="Token address if token transaction")
    status: str = Field(..., description="Transaction status")

class WalletAnalysisResponse(BaseModel):
    """Wallet analysis response model."""
    wallet_address: str = Field(..., description="Analyzed wallet address")
    balance: Dict[str, Decimal] = Field(..., description="Token balances")
    transaction_count: int = Field(..., description="Total transaction count")
    transactions: Optional[List[TransactionInfo]] = Field(None, description="Recent transactions")
    risk_score: Optional[float] = Field(None, description="Wallet risk score")
    last_activity: Optional[datetime] = Field(None, description="Last wallet activity")

class PerformanceMetrics(BaseModel):
    """Performance metrics model."""
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    request_count: int = Field(..., description="Total request count")
    average_response_time: float = Field(..., description="Average response time in ms")
    error_count: int = Field(..., description="Total error count")
    cache_hit_ratio: Optional[float] = Field(None, description="Cache hit ratio")

class ErrorResponse(BaseModel):
    """Error response model."""
    message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    details: Optional[Dict] = Field(None, description="Error details")
    timestamp: datetime = Field(..., description="Error timestamp")
