from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Token(Base):
    __tablename__ = 'tokens'
    
    id = Column(Integer, primary_key=True)
    address = Column(String(44), unique=True, nullable=False)
    name = Column(String(100))
    symbol = Column(String(20))
    decimals = Column(Integer)
    total_supply = Column(Float)
    holder_count = Column(Integer)
    is_verified = Column(Boolean, default=False)
    token_metadata = Column(JSON)  
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prices = relationship("TokenPrice", back_populates="token")
    holders = relationship("TokenHolder", back_populates="token")
    transactions = relationship("TokenTransaction", back_populates="token")
    
    # Indexes
    __table_args__ = (
        Index('idx_token_address', 'address'),
        Index('idx_token_symbol', 'symbol'),
        Index('idx_token_holder_count', 'holder_count'),
    )

class TokenPrice(Base):
    __tablename__ = 'token_prices'
    
    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey('tokens.id'), nullable=False)
    price_usd = Column(Float)
    volume_24h = Column(Float)
    market_cap = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(50))  
    
    # Relationships
    token = relationship("Token", back_populates="prices")
    
    # Indexes
    __table_args__ = (
        Index('idx_token_price_time', 'token_id', 'timestamp'),
        Index('idx_price_timestamp', 'timestamp'),
    )

class TokenHolder(Base):
    __tablename__ = 'token_holders'
    
    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey('tokens.id'), nullable=False)
    wallet_address = Column(String(44), nullable=False)
    balance = Column(Float)
    percentage = Column(Float)
    first_seen = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    token = relationship("Token", back_populates="holders")
    
    # Indexes
    __table_args__ = (
        Index('idx_holder_token', 'token_id', 'wallet_address'),
        Index('idx_holder_balance', 'token_id', 'balance'),
    )

class TokenTransaction(Base):
    __tablename__ = 'token_transactions'
    
    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey('tokens.id'), nullable=False)
    transaction_hash = Column(String(88), nullable=False)
    from_address = Column(String(44))
    to_address = Column(String(44))
    amount = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    block_number = Column(Integer)
    
    # Relationships
    token = relationship("Token", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_tx_token_time', 'token_id', 'timestamp'),
        Index('idx_tx_addresses', 'from_address', 'to_address'),
    )

class WalletAnalysis(Base):
    __tablename__ = 'wallet_analyses'
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(44), nullable=False)
    token_count = Column(Integer)
    total_value_usd = Column(Float)
    transaction_count = Column(Integer)
    first_transaction = Column(DateTime)
    last_transaction = Column(DateTime)
    analysis_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_wallet_address', 'wallet_address'),
        Index('idx_wallet_value', 'total_value_usd'),
    )

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey('tokens.id'))
    alert_type = Column(String(50))  
    threshold = Column(Float)
    is_active = Column(Boolean, default=True)
    notification_channels = Column(JSON)  
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime)
    
    # Indexes
    __table_args__ = (
        Index('idx_alert_token', 'token_id'),
        Index('idx_alert_type', 'alert_type'),
    )

class SystemMetric(Base):
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True)
    metric_type = Column(String(50))  
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_metric_time', 'metric_type', 'timestamp'),
    )
