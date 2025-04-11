from typing import Optional, Union
from datetime import datetime, timedelta
from asyncpg import Pool, Connection
from src.database.models import SecretCache

async def create_secret(pool: Pool, key: str, secret: SecretCache):
    async with pool.acquire() as connection:
        result = await connection.execute(
            "INSERT INTO secrets (secret_key, encrypted_value, passphrase, ttl_seconds, created_at) VALUES ($1, $2, $3, $4, $5)",
            key, secret.value.decode(), secret.passphrase, secret.ttl_seconds, secret.created_at)
        return result

async def get_secret(pool: Pool, key: str, passphrase: str) -> Optional[Union[str, int]]:
    async with pool.acquire() as connection:
        async with connection.transaction():
            record = await get_query(connection, key)
            if record:
                secret = SecretCache(value=record["encrypted_value"], passphrase=record["passphrase"],
                                     ttl_seconds=record["ttl_seconds"], created_at=record["created_at"])

                if secret.passphrase is not None and passphrase != secret.passphrase:
                    return 403
                if secret.ttl_seconds is not None:
                    if datetime.utcnow() - secret.created_at >= timedelta(seconds=secret.ttl_seconds):
                        await delete_query(connection, key)
                        return 410
                await delete_query(connection, key)
                return secret.value
            return None

async def delete_query(connection: Connection, key: str):
    return await connection.execute("DELETE FROM secrets WHERE secret_key = $1", key)

async def get_query(connection: Connection, key: str):
    return await connection.fetchrow(
        "SELECT encrypted_value, passphrase, ttl_seconds, created_at FROM secrets WHERE secret_key = $1", key)

async def delete_secret(pool: Pool, key: str, passphrase: str) -> int:
    async with pool.acquire() as connection:
        async with connection.transaction():
            record = await get_query(connection, key)
            if record:
                record_passphrase = record["passphrase"]
                if record_passphrase is not None and passphrase != record_passphrase:
                    return 403
                await delete_query(connection, key)
                return 200
            return 404

