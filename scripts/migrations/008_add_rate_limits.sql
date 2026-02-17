-- Migration: 008 - Add rate_limits table for Zeabur deployment
-- Feature: 008-zeabur-deployment
-- Purpose: Track API rate limiting per IP address (20 requests per hour)
-- Date: 2025-02-17

CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    window_start TIMESTAMP NOT NULL,
    last_request TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast IP lookup (primary query pattern)
CREATE INDEX IF NOT EXISTS idx_rate_limits_ip ON rate_limits(ip_address);

-- Index for window-based queries (cleanup and expiration checks)
CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(window_start);

-- Index for cleanup operations (delete old entries)
CREATE INDEX IF NOT EXISTS idx_rate_limits_last_request ON rate_limits(last_request);

-- Verify table creation
SELECT 'rate_limits table created successfully' AS status;
