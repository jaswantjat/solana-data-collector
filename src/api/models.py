"""API request and response models."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal

class TokenAnalysisRequest(BaseModel):
    """Token analysis request model."""
    token_address: str = Field(
        ...,
        description="Solana token address to analyze",
        min_length=32,
        max_length=44
    )
    include_history: bool = Field(
        False,
        description="Include historical price and volume data"
    )
    time_range: Optional[str] = Field(
        None,
        description="Time range for historical data (e.g., '1d', '7d', '30d')"
    )

    @validator('token_address')
    def validate_token_address(cls, v):
        """Validate token address format."""
        if not v.isalnum():
            raise ValueError("Token address must be alphanumeric")
        return v

class TokenMetrics(BaseModel):
    """Token metrics model."""
    price_usd: Decimal = Field(..., description="Current price in USD")
    market_cap: Decimal = Field(..., description="Market capitalization in USD")
    volume_24h: Decimal = Field(..., description="24-hour trading volume")
    price_change_24h: float = Field(..., description="24-hour price change percentage")
    liquidity_usd: Decimal = Field(..., description="Total liquidity in USD")
    holder_count: int = Field(..., description="Number of token holders")
    created_at: datetime = Field(..., description="Token creation timestamp")

class TokenRiskMetrics(BaseModel):
    """Token risk assessment metrics."""
    risk_score: float = Field(
        ...,
        description="Overall risk score (0-100)",
        ge=0,
        le=100
    )
    liquidity_risk: float = Field(
        ...,
        description="Liquidity risk score",
        ge=0,
        le=100
    )
    concentration_risk: float = Field(
        ...,
        description="Holder concentration risk score",
        ge=0,
        le=100
    )
    volatility_risk: float = Field(
        ...,
        description="Price volatility risk score",
        ge=0,
        le=100
    )
    contract_risk: float = Field(
        ...,
        description="Smart contract risk score",
        ge=0,
        le=100
    )

class TokenHistoricalData(BaseModel):
    """Token historical data model."""
    timestamp: datetime = Field(..., description="Data point timestamp")
    price_usd: Decimal = Field(..., description="Price in USD")
    volume_usd: Decimal = Field(..., description="Trading volume in USD")
    liquidity_usd: Decimal = Field(..., description="Liquidity in USD")

class TokenAnalysisResponse(BaseModel):
    """Token analysis response model."""
    token_address: str = Field(..., description="Analyzed token address")
    token_name: str = Field(..., description="Token name")
    token_symbol: str = Field(..., description="Token symbol")
    metrics: TokenMetrics = Field(..., description="Current token metrics")
    risk_assessment: TokenRiskMetrics = Field(
        ...,
        description="Risk assessment metrics"
    )
    historical_data: Optional[List[TokenHistoricalData]] = Field(
        None,
        description="Historical price and volume data"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Analysis timestamp"
    )

class WalletAnalysisRequest(BaseModel):
    """Wallet analysis request model."""
    wallet_address: str = Field(
        ...,
        description="Solana wallet address to analyze",
        min_length=32,
        max_length=44
    )
    include_transactions: bool = Field(
        False,
        description="Include recent transactions"
    )
    max_transactions: Optional[int] = Field(
        None,
        description="Maximum number of transactions to return",
        gt=0,
        le=1000
    )

    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        """Validate wallet address format."""
        if not v.isalnum():
            raise ValueError("Wallet address must be alphanumeric")
        return v

class WalletMetrics(BaseModel):
    """Wallet metrics model."""
    balance_sol: Decimal = Field(..., description="SOL balance")
    balance_usd: Decimal = Field(..., description="Total balance in USD")
    token_count: int = Field(..., description="Number of tokens held")
    transaction_count: int = Field(..., description="Total transaction count")
    first_activity: datetime = Field(..., description="First activity timestamp")
    last_activity: datetime = Field(..., description="Last activity timestamp")

class WalletToken(BaseModel):
    """Wallet token holding model."""
    token_address: str = Field(..., description="Token address")
    token_name: str = Field(..., description="Token name")
    token_symbol: str = Field(..., description="Token symbol")
    balance: Decimal = Field(..., description="Token balance")
    value_usd: Decimal = Field(..., description="Value in USD")
    percentage: float = Field(
        ...,
        description="Percentage of total portfolio value"
    )

class Transaction(BaseModel):
    """Transaction model."""
    signature: str = Field(..., description="Transaction signature")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    type: str = Field(..., description="Transaction type")
    status: str = Field(..., description="Transaction status")
    amount: Decimal = Field(..., description="Transaction amount")
    fee: Decimal = Field(..., description="Transaction fee")
    token_address: Optional[str] = Field(
        None,
        description="Token address if token transaction"
    )

class WalletRiskMetrics(BaseModel):
    """Wallet risk assessment metrics."""
    risk_score: float = Field(
        ...,
        description="Overall risk score (0-100)",
        ge=0,
        le=100
    )
    interaction_risk: float = Field(
        ...,
        description="Risk based on interactions with other wallets",
        ge=0,
        le=100
    )
    token_risk: float = Field(
        ...,
        description="Risk based on held tokens",
        ge=0,
        le=100
    )
    activity_risk: float = Field(
        ...,
        description="Risk based on activity patterns",
        ge=0,
        le=100
    )

class WalletAnalysisResponse(BaseModel):
    """Wallet analysis response model."""
    wallet_address: str = Field(..., description="Analyzed wallet address")
    metrics: WalletMetrics = Field(..., description="Wallet metrics")
    risk_assessment: WalletRiskMetrics = Field(
        ...,
        description="Risk assessment metrics"
    )
    tokens: List[WalletToken] = Field(..., description="Token holdings")
    recent_transactions: Optional[List[Transaction]] = Field(
        None,
        description="Recent transactions"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Analysis timestamp"
    )

class BlacklistInfo(BaseModel):
    """Blacklist information model."""
    address: str = Field(..., description="Blacklisted address")
    reason: str = Field(..., description="Reason for blacklisting")
    scam_amount: Decimal = Field(
        0,
        description="Amount involved in scam (if applicable)"
    )
    token_address: Optional[str] = Field(
        None,
        description="Associated token address"
    )
    timestamp: datetime = Field(
        ...,
        description="Blacklist entry timestamp"
    )

class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response model."""
    response_time: float = Field(
        ...,
        description="Average response time in seconds"
    )
    cpu_usage: float = Field(
        ...,
        description="CPU usage percentage",
        ge=0,
        le=100
    )
    memory_usage: float = Field(
        ...,
        description="Memory usage percentage",
        ge=0,
        le=100
    )
    cache_hit_rate: float = Field(
        ...,
        description="Cache hit rate percentage",
        ge=0,
        le=100
    )
    request_count: int = Field(
        ...,
        description="Total request count"
    )
    error_count: int = Field(
        ...,
        description="Total error count"
    )
    last_update: datetime = Field(
        ...,
        description="Last update timestamp"
    )

class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = Field("error", description="Response status")
    message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )
