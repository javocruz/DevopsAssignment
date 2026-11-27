CREATE TABLE dbo.bets (
    id INT IDENTITY PRIMARY KEY,
    estimate_id INT NOT NULL UNIQUE,
    market_id NVARCHAR(128) NOT NULL,
    decider NVARCHAR(32) NOT NULL,
    context_level NVARCHAR(32) NOT NULL,
    side NVARCHAR(3) NOT NULL,
    entry_price FLOAT NOT NULL,
    stake FLOAT NOT NULL,
    shares FLOAT NOT NULL,
    status NVARCHAR(16) NOT NULL,
    pnl FLOAT,
    placed_at NVARCHAR(32) NOT NULL,
    settled_at NVARCHAR(32)
);

CREATE TABLE dbo.intel_cache (
    [key] NVARCHAR(256) PRIMARY KEY,
    payload NVARCHAR(MAX) NOT NULL,
    fetched_at NVARCHAR(32) NOT NULL
);
