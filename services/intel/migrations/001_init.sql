CREATE TABLE dbo.markets (
    id NVARCHAR(128) PRIMARY KEY,
    question NVARCHAR(MAX) NOT NULL,
    rules NVARCHAR(MAX),
    category NVARCHAR(256),
    end_date NVARCHAR(32),
    news_query NVARCHAR(MAX),
    analyst_notes NVARCHAR(MAX),
    source NVARCHAR(32) NOT NULL,
    status NVARCHAR(32) NOT NULL,
    outcome INT
);

CREATE TABLE dbo.price_snapshots (
    id INT IDENTITY PRIMARY KEY,
    market_id NVARCHAR(128) NOT NULL REFERENCES dbo.markets(id),
    yes_price FLOAT NOT NULL,
    captured_at NVARCHAR(32) NOT NULL,
    UNIQUE (market_id, captured_at)
);

CREATE TABLE dbo.news_items (
    id INT IDENTITY PRIMARY KEY,
    market_id NVARCHAR(128) NOT NULL REFERENCES dbo.markets(id),
    title NVARCHAR(MAX) NOT NULL,
    description NVARCHAR(MAX),
    source NVARCHAR(MAX),
    url NVARCHAR(MAX) NOT NULL,
    -- Index a fixed-size digest so long article URLs fit the unique key.
    url_hash AS CONVERT(BINARY(32), HASHBYTES('SHA2_256', url)) PERSISTED,
    published_at NVARCHAR(32) NOT NULL,
    fetched_at NVARCHAR(32) NOT NULL,
    UNIQUE (market_id, url_hash)
);

CREATE TABLE dbo.estimates (
    id INT IDENTITY PRIMARY KEY,
    market_id NVARCHAR(128) NOT NULL REFERENCES dbo.markets(id),
    snapshot_id INT NOT NULL REFERENCES dbo.price_snapshots(id),
    decider NVARCHAR(32) NOT NULL,
    context_level NVARCHAR(32) NOT NULL,
    jev_prob FLOAT NOT NULL,
    info_score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    category NVARCHAR(256),
    state_json NVARCHAR(MAX) NOT NULL,
    created_at NVARCHAR(32) NOT NULL,
    UNIQUE (market_id, snapshot_id, decider, context_level)
);
