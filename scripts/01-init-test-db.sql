-- Create test database for integration tests
-- This script runs automatically when the postgres container is first initialized

CREATE DATABASE fundamental_analysis_test;

-- Grant permissions to postgres user (already owner, but explicit for clarity)
GRANT ALL PRIVILEGES ON DATABASE fundamental_analysis_test TO postgres;
