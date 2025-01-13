-- Create tokens table
CREATE TABLE IF NOT EXISTS tokens (
    id SERIAL PRIMARY KEY,
    address VARCHAR(44) UNIQUE NOT NULL,
    name VARCHAR(100),
    symbol VARCHAR(20),
    decimals INTEGER,
    total_supply DOUBLE PRECISION,
    holder_count INTEGER,
    is_verified BOOLEAN DEFAULT false,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_token_address ON tokens(address);
CREATE INDEX IF NOT EXISTS idx_token_symbol ON tokens(symbol);
CREATE INDEX IF NOT EXISTS idx_token_holder_count ON tokens(holder_count);

-- Create token_prices table
CREATE TABLE IF NOT EXISTS token_prices (
    id SERIAL PRIMARY KEY,
    token_id INTEGER REFERENCES tokens(id) NOT NULL,
    price_usd DOUBLE PRECISION,
    volume_24h DOUBLE PRECISION,
    market_cap DOUBLE PRECISION,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_token_price_time ON token_prices(token_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_price_timestamp ON token_prices(timestamp);

-- Create token_holders table
CREATE TABLE IF NOT EXISTS token_holders (
    id SERIAL PRIMARY KEY,
    token_id INTEGER REFERENCES tokens(id) NOT NULL,
    wallet_address VARCHAR(44) NOT NULL,
    balance DOUBLE PRECISION,
    percentage DOUBLE PRECISION,
    first_seen TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_holder_token ON token_holders(token_id, wallet_address);
CREATE INDEX IF NOT EXISTS idx_holder_balance ON token_holders(token_id, balance);

-- Create token_transactions table
CREATE TABLE IF NOT EXISTS token_transactions (
    id SERIAL PRIMARY KEY,
    token_id INTEGER REFERENCES tokens(id) NOT NULL,
    transaction_hash VARCHAR(88) NOT NULL,
    from_address VARCHAR(44),
    to_address VARCHAR(44),
    amount DOUBLE PRECISION,
    timestamp TIMESTAMP NOT NULL,
    block_number INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tx_token_time ON token_transactions(token_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_tx_addresses ON token_transactions(from_address, to_address);

-- Create wallet_analyses table
CREATE TABLE IF NOT EXISTS wallet_analyses (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(44) NOT NULL,
    token_count INTEGER,
    total_value_usd DOUBLE PRECISION,
    transaction_count INTEGER,
    first_transaction TIMESTAMP,
    last_transaction TIMESTAMP,
    analysis_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wallet_address ON wallet_analyses(wallet_address);
CREATE INDEX IF NOT EXISTS idx_wallet_value ON wallet_analyses(total_value_usd);

-- Create alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    token_id INTEGER REFERENCES tokens(id),
    alert_type VARCHAR(50),
    threshold DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT true,
    notification_channels JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_token ON alerts(token_id);
CREATE INDEX IF NOT EXISTS idx_alert_type ON alerts(alert_type);

-- Create system_metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_type VARCHAR(50),
    value DOUBLE PRECISION,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metric_time ON system_metrics(metric_type, timestamp);

-- Create functions and triggers
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tokens_updated_at
    BEFORE UPDATE ON tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Create materialized views for performance
CREATE MATERIALIZED VIEW IF NOT EXISTS token_stats AS
SELECT 
    t.id,
    t.address,
    t.symbol,
    t.holder_count,
    tp.price_usd,
    tp.volume_24h,
    tp.market_cap,
    COUNT(tx.id) as transaction_count,
    MAX(tx.timestamp) as last_transaction
FROM tokens t
LEFT JOIN token_prices tp ON t.id = tp.token_id
LEFT JOIN token_transactions tx ON t.id = tx.token_id
GROUP BY t.id, t.address, t.symbol, t.holder_count, tp.price_usd, tp.volume_24h, tp.market_cap;

CREATE UNIQUE INDEX IF NOT EXISTS idx_token_stats_id ON token_stats(id);

-- Create function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_token_stats()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY token_stats;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to refresh materialized view
CREATE TRIGGER refresh_token_stats_on_price
    AFTER INSERT OR UPDATE OR DELETE ON token_prices
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_token_stats();

CREATE TRIGGER refresh_token_stats_on_tx
    AFTER INSERT OR UPDATE OR DELETE ON token_transactions
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_token_stats();
