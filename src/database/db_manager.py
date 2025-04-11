import asyncpg

async def init_db(database_url: str) -> asyncpg.pool:
    await create_tables(database_url)
    return await asyncpg.create_pool(dsn=database_url)

async def clean_expired_secrets(connection: asyncpg.Connection):
    return await connection.execute("""
    DELETE FROM secrets
                    WHERE created_at < timezone('UTC', now())::TIMESTAMP - (ttl_seconds || 'seconds')::INTERVAL;
    """)

async def create_tables(database_url):
    connection: asyncpg.Connection = await asyncpg.connect(database_url)
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS secrets (
            secret_key TEXT PRIMARY KEY,
            encrypted_value TEXT NOT NULL,
            passphrase TEXT,
            ttl_seconds INTEGER,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """)
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            secret_key TEXT,
            event_type VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            ip_address VARCHAR(50) NOT NULL,
            metadata JSONB
        )
        """)
    await connection.close()
