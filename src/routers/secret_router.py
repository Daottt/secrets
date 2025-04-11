import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from cryptography.fernet import Fernet
from src.database.models import Secret, SecretCache
from src.cache_manager import CacheManager
from src.resolvers.secret_resolver import create_secret, get_secret, delete_secret
from src.resolvers.log_resolver import log_event, EventType

class SecretRouter:
    def __init__(self, cache_manager, encoder, connection_pool):
        self.cache_manager: CacheManager = cache_manager
        self.fernet: Fernet = encoder
        self.connection_pool = connection_pool
        self.fastapi_router: APIRouter = APIRouter(prefix="/secret")
        self.add_endpoints()

    def add_endpoints(self):

        @self.fastapi_router.post("")
        async def post(secret: Secret, request: Request) -> JSONResponse:
            secret_uuid = str(uuid.uuid4())
            secret.value = self.fernet.encrypt(secret.value.encode())
            secret = SecretCache(**secret.model_dump(), created_at=datetime.utcnow())

            await create_secret(self.connection_pool, secret_uuid, secret)
            await self.cache_manager.create_secret_cache(secret_uuid, secret)
            await log_event(self.connection_pool, secret_uuid, EventType.create, request.client.host,
                            {"ttl": secret.ttl_seconds})
            return JSONResponse(content={"secret_key": secret_uuid})

        @self.fastapi_router.get("/{secret_key}")
        async def get_by_key(key: str, request: Request, passphrase: Optional[str] = None) -> JSONResponse:
            cache_secret = await self.cache_manager.get_secret_value(key, passphrase)
            if type(cache_secret) is int:
                match cache_secret:
                    case 403:
                        raise HTTPException(status_code=403, detail="Incorrect passphrase")
                    case 410:
                        await delete_secret(self.connection_pool, key, passphrase)
                        raise HTTPException(status_code=410, detail="Secret expired")
                    case _:
                        raise HTTPException(status_code=500)
            if cache_secret:
                await delete_secret(self.connection_pool, key, passphrase)
                await log_event(self.connection_pool, key, EventType.get_cache, request.client.host, {})
                return JSONResponse(content={"secret": self.fernet.decrypt(cache_secret).decode()})

            db_secret = await get_secret(self.connection_pool, key, passphrase)
            if type(db_secret) is int:
                match db_secret:
                    case 403:
                        raise HTTPException(status_code=403, detail="Incorrect passphrase")
                    case 410:
                        raise HTTPException(status_code=410, detail="Secret expired")
                    case _:
                        raise HTTPException(status_code=500)
            if db_secret:
                await log_event(self.connection_pool, key, EventType.get_db, request.client.host, {})
                return JSONResponse(content={"secret_db": self.fernet.decrypt(db_secret).decode()})
            raise HTTPException(status_code=404, detail="Secret not found")

        @self.fastapi_router.delete("/{secret_key}")
        async def delete_by_key(key: str, request: Request, passphrase: Optional[str] = None) -> JSONResponse:
            await self.cache_manager.delete_secret(key, passphrase)
            result = await delete_secret(self.connection_pool, key, passphrase)
            match result:
                case 200:
                    await log_event(self.connection_pool, key, EventType.delete, request.client.host, {})
                    return JSONResponse(content={"status": "secret_deleted"})
                case 403:
                    raise HTTPException(status_code=403, detail="Incorrect passphrase")
            raise HTTPException(status_code=404, detail="Secret not found")
