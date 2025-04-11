import json
import enum
from datetime import datetime
from typing import Dict
from asyncpg import Pool

class EventType(enum.Enum):
    create = "create"
    get_cache = "get_cache"
    get_db = "get_db"
    delete = "delete"
    cleanup = "cleanup"


async def log_event(pool: Pool, key: str, event_type: EventType, ip_address: str, metadata: Dict):
    async with pool.acquire() as connection:
        await connection.execute(
            "INSERT INTO logs (secret_key, event_type, timestamp, ip_address, metadata) VALUES($1, $2, $3, $4, $5)",
            key, event_type.value, datetime.utcnow(), ip_address, json.dumps(metadata))
