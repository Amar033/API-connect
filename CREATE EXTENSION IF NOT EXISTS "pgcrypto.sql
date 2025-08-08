CREATE EXTENSION IF NOT EXISTS "pgcrypto"  --create uuid generation encryption 

--users TABLE
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


--external db credentials
CREATE TABLE external_db_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100),
    db_owner_username VARCHAR(100),
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    dbname TEXT NOT NULL,
    db_user TEXT NOT NULL,
    db_password TEXT NOT NULL, -- Prefer encrypted storage in production
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


