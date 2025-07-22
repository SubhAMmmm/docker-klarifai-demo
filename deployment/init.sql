-- Database initialization script
-- This runs when PostgreSQL container starts for the first time

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database if it doesn't exist (though docker-compose should handle this)
-- Note: This is redundant as POSTGRES_DB in docker-compose creates the database

-- Set up basic configurations
-- These are run as the postgres user, so they apply to the entire database instance

-- You can add any database-level configurations here
-- For example, setting timezone, locale, etc.

-- Note: Django tables will be created via migrations after the container starts
-- This file is mainly for extensions and database-level configurations

-- Optional: Create a schema for your app (if needed)
-- CREATE SCHEMA IF NOT EXISTS api;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END
$$;