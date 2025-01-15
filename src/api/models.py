"""API request and response models."""
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TokenAnalysisRequest(BaseModel):
    """Request model for token analysis."""
    token_address: str = Field(..., description="Token contract address")
    include_holder_analysis: bool = Field(
        True,
        description="Whether to include holder analysis"
    )
    include_twitter_analysis: bool = Field(
        True,
        description="Whether to include Twitter analysis"
    )

class TokenAnalysisResponse(BaseModel):
    """Response model for token analysis."""
    token_address: str = Field(..., description="Token contract address")
    is_suspicious: bool = Field(..., description="Whether the token is suspicious")
    risk_factors: List[str] = Field(
        ...,
        description="List of identified risk factors"
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score of the analysis",
        ge=0.0,
        le=1.0
    )
    analysis_timestamp: datetime = Field(
        ...,
        description="Timestamp of the analysis"
    )

class WalletAnalysisRequest(BaseModel):
    """Request model for wallet analysis."""
    wallet_address: str = Field(..., description="Wallet address to analyze")
    include_transaction_history: bool = Field(
        True,
        description="Whether to include transaction history"
    )

class Transaction(BaseModel):
    """Model for a transaction."""
    timestamp: datetime
    transaction_hash: str
    token_address: Optional[str]
    amount: float
    transaction_type: str
    risk_score: Optional[float]

class WalletAnalysisResponse(BaseModel):
    """Response model for wallet analysis."""
    wallet_address: str = Field(..., description="Analyzed wallet address")
    risk_score: float = Field(
        ...,
        description="Overall risk score",
        ge=0.0,
        le=1.0
    )
    suspicious_transactions: List[Transaction] = Field(
        ...,
        description="List of suspicious transactions"
    )
    analysis_timestamp: datetime = Field(
        ...,
        description="Timestamp of the analysis"
    )

class BlacklistedDeployer(BaseModel):
    """Model for a blacklisted deployer."""
    address: str = Field(..., description="Deployer address")
    reason: str = Field(..., description="Reason for blacklisting")
    scam_amount: float = Field(
        0.0,
        description="Amount involved in scam"
    )
    token_address: Optional[str] = Field(
        None,
        description="Associated token address"
    )
    timestamp: datetime = Field(
        ...,
        description="When the deployer was blacklisted"
    )

class BlacklistInfo(BaseModel):
    """Response model for blacklist statistics."""
    total_blacklisted: int = Field(
        ...,
        description="Total number of blacklisted addresses"
    )
    total_scam_amount: float = Field(
        ...,
        description="Total amount involved in scams"
    )
    recent_additions: List[BlacklistedDeployer] = Field(
        ...,
        description="Recently blacklisted deployers"
    )

class PerformanceMetrics(BaseModel):
    """Model for performance metrics."""
    response_time: float = Field(
        ...,
        description="Average response time in seconds"
    )
    cpu_usage: float = Field(
        ...,
        description="CPU usage percentage"
    )
    memory_usage: float = Field(
        ...,
        description="Memory usage percentage"
    )
    cache_hit_rate: float = Field(
        ...,
        description="Cache hit rate percentage"
    )
    request_rate: float = Field(
        ...,
        description="Requests per second"
    )
    error_rate: float = Field(
        ...,
        description="Errors per request"
    )

class MonitoringStatus(BaseModel):
    """Response model for monitoring status."""
    status: str = Field(..., description="Current status")
    last_update: datetime = Field(
        ...,
        description="Last update timestamp"
    )
    monitored_tokens: int = Field(
        ...,
        description="Number of tokens being monitored"
    )
    active_alerts: int = Field(
        ...,
        description="Number of active alerts"
    )
    performance_metrics: Optional[PerformanceMetrics] = Field(
        None,
        description="Current performance metrics"
    )
