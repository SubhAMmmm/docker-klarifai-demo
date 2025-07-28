-- Initialize PostgreSQL database with pgvector extension
-- This script runs automatically when the database container starts

-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create additional extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create a user for your application (optional, if different from postgres)
-- DO $$ 
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'klarifai_user') THEN
--         CREATE ROLE klarifai_user WITH LOGIN PASSWORD 'your_app_password';
--         GRANT ALL PRIVILEGES ON DATABASE data_analysis_prod TO klarifai_user;
--     END IF;
-- END
-- $$;

-- Set default settings
ALTER DATABASE data_analysis_prod SET timezone TO 'UTC';