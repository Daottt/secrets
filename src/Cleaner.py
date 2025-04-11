import asyncio
from asyncpg import Pool
from src.database.db_manager import clean_expired_secrets
from src.cache_manager import CacheManager
from src.resolvers.log_resolver import log_event, EventType

async def cleanup_expired_data(cleanup_interval_seconds: int, connection_pool: Pool,
                               cache_manager: CacheManager, cache_expiry_seconds: int):
    while True:
        async with connection_pool.acquire() as connection:
            db_count = await clean_expired_secrets(connection)
            cache_count = await cache_manager.clean_expired_cache(cache_expiry_seconds)
            await log_event(connection_pool, "1", EventType.cleanup, "local",
                            {"db": db_count.split(" ")[1], "cache": cache_count})
        await asyncio.sleep(cleanup_interval_seconds)
