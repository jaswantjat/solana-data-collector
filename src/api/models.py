"""API models for request and response validation."""
from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
from decimal import Decimal

from src.api.errors import ValidationError

class TokenInfo(BaseModel):
    """Token information model."""
    address: str = Field(..., description="Token address", min_length=44, max_length=44)
    symbol: str = Field(..., description="Token symbol", max_length=10)
    name: str = Field(..., description="Token name", max_length=100)
    decimals: int = Field(..., description="Token decimals", ge=0, le=18)

    @validator('address')
    def validate_address(cls, v):
        """Validate Solana address format."""
        if not v.isalnum():
            raise ValidationError(
                message="Token address must be alphanumeric",
                details={"address": v}
            )
        return v

class PriceInfo(BaseModel):
    """Price information model."""
    price: Decimal = Field(..., description="Current price", ge=0)
    price_change_24h: Optional[Decimal] = Field(None, description="24h price change percentage")
    volume_24h: Optional[Decimal] = Field(None, description="24h trading volume", ge=0)
    market_cap: Optional[Decimal] = Field(None, description="Market capitalization", ge=0)

    @root_validator
    def validate_price_data(cls, values):
        """Validate price-related data."""
        if values.get('market_cap') is not None and values.get('price'):
            if values['market_cap'] < values['price']:
                raise ValidationError(
                    message="Market cap cannot be less than price",
                    details={"market_cap": values['market_cap'], "price": values['price']}
                )
        return values

class TokenAnalysisRequest(BaseModel):
    """Token analysis request model."""
    token_address: str = Field(..., description="Token address to analyze", min_length=44, max_length=44)
    include_price_history: bool = Field(False, description="Include price history in response")
    time_range: Optional[str] = Field(None, description="Time range for analysis (e.g., '1d', '7d', '30d')")

    @validator('token_address')
    def validate_token_address(cls, v):
        """Validate Solana token address."""
        if not v.isalnum():
            raise ValidationError(
                message="Token address must be alphanumeric",
                details={"token_address": v}
            )
        return v

    @validator('time_range')
    def validate_time_range(cls, v):
        """Validate time range format."""
        if v is not None and v not in ['1d', '7d', '30d', '90d']:
            raise ValidationError(
                message="Invalid time range",
                details={"time_range": v, "allowed_values": ['1d', '7d', '30d', '90d']}
            )
        return v

class TokenAnalysisResponse(BaseModel):
    """Token analysis response model."""
    token: TokenInfo
    price_info: PriceInfo
    holders_count: Optional[int] = Field(None, description="Number of token holders", ge=0)
    price_history: Optional[List[Dict[str, Union[datetime, Decimal]]]] = Field(
        None, description="Historical price data"
    )
    risk_metrics: Optional[Dict[str, Union[str, float]]] = Field(
        None, description="Risk assessment metrics"
    )

    @validator('price_history')
    def validate_price_history(cls, v):
        """Validate price history data."""
        if v is not None:
            for entry in v:
                if 'timestamp' not in entry or 'price' not in entry:
                    raise ValidationError(
                        message="Invalid price history entry",
                        details={"entry": entry, "required_fields": ['timestamp', 'price']}
                    )
                if entry['price'] < 0:
                    raise ValidationError(
                        message="Price cannot be negative",
                        details={"price": entry['price']}
                    )
        return v

class WalletAnalysisRequest(BaseModel):
    """Wallet analysis request model."""
    wallet_address: str = Field(..., description="Wallet address to analyze", min_length=44, max_length=44)
    include_transaction_history: bool = Field(False, description="Include transaction history")
    time_range: Optional[str] = Field(None, description="Time range for analysis")

    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        """Validate Solana wallet address."""
        if not v.isalnum():
            raise ValidationError(
                message="Wallet address must be alphanumeric",
                details={"wallet_address": v}
            )
        return v

    @validator('time_range')
    def validate_time_range(cls, v):
        """Validate time range format."""
        if v is not None and v not in ['1d', '7d', '30d', '90d']:
            raise ValidationError(
                message="Invalid time range",
                details={"time_range": v, "allowed_values": ['1d', '7d', '30d', '90d']}
            )
        return v

class TransactionInfo(BaseModel):
    """Transaction information model."""
    signature: str = Field(..., description="Transaction signature", min_length=64, max_length=128)
    timestamp: datetime = Field(..., description="Transaction timestamp")
    type: str = Field(..., description="Transaction type")
    amount: Optional[Decimal] = Field(None, description="Transaction amount", ge=0)
    token_address: Optional[str] = Field(None, description="Token address if token transaction")
    status: str = Field(..., description="Transaction status")

    @validator('type')
    def validate_type(cls, v):
        """Validate transaction type."""
        allowed_types = ['transfer', 'swap', 'mint', 'burn', 'other']
        if v not in allowed_types:
            raise ValidationError(
                message="Invalid transaction type",
                details={"type": v, "allowed_types": allowed_types}
            )
        return v

    @validator('status')
    def validate_status(cls, v):
        """Validate transaction status."""
        allowed_statuses = ['success', 'failed', 'pending']
        if v not in allowed_statuses:
            raise ValidationError(
                message="Invalid transaction status",
                details={"status": v, "allowed_statuses": allowed_statuses}
            )
        return v

class WalletAnalysisResponse(BaseModel):
    """Wallet analysis response model."""
    wallet_address: str = Field(..., description="Analyzed wallet address")
    balance: Dict[str, Decimal] = Field(..., description="Token balances")
    transaction_count: int = Field(..., description="Total transaction count", ge=0)
    transactions: Optional[List[TransactionInfo]] = Field(None, description="Recent transactions")
    risk_score: Optional[float] = Field(None, description="Wallet risk score", ge=0, le=100)
    last_activity: Optional[datetime] = Field(None, description="Last wallet activity")

    @validator('balance')
    def validate_balances(cls, v):
        """Validate token balances."""
        for token, amount in v.items():
            if amount < 0:
                raise ValidationError(
                    message="Token balance cannot be negative",
                    details={"token": token, "balance": amount}
                )
        return v

class PerformanceMetrics(BaseModel):
    """Performance metrics model."""
    cpu_usage: float = Field(..., description="CPU usage percentage", ge=0, le=100)
    memory_usage: float = Field(..., description="Memory usage percentage", ge=0, le=100)
    disk_usage: float = Field(..., description="Disk usage percentage", ge=0, le=100)
    request_count: int = Field(..., description="Total request count", ge=0)
    average_response_time: float = Field(..., description="Average response time in ms", ge=0)
    error_count: int = Field(..., description="Total error count", ge=0)
    cache_hit_ratio: Optional[float] = Field(None, description="Cache hit ratio", ge=0, le=1)

    @validator('cpu_usage', 'memory_usage', 'disk_usage')
    def validate_metrics(cls, v, field):
        """Validate performance metrics."""
        if v < 0 or v > 100:
            raise ValidationError(
                message=f"{field.name} must be between 0 and 100",
                details={field.name: v}
            )
        return v

class ErrorResponse(BaseModel):
    """Error response model."""
    message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    details: Optional[Dict] = Field(None, description="Error details")
    timestamp: datetime = Field(..., description="Error timestamp")
