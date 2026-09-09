-- Initial database setup for {{ project_name }}
-- Ensure databases exist for application and Langfuse
SELECT 'CREATE DATABASE {{ project_name_snake }}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{{ project_name_snake }}')\gexec

SELECT 'CREATE DATABASE langfuse'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec

-- Connect to project database and configure extensions
\c {{ project_name_snake }}
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Connect to Langfuse database and configure extensions
\c langfuse
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Reconnect to default project database
\c {{ project_name_snake }}
