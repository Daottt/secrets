import asyncio
import os
from contextlib import asynccontextmanager
import fastapi
import uvicorn
from dotenv import find_dotenv, load_dotenv
from cryptography.fernet import Fernet
from src.cache_manager import CacheManager
from src.routers.secret_router import SecretRouter
from src.database.db_manager import init_db
from src.Cleaner import cleanup_expired_data

load_dotenv(find_dotenv())
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/db")
CACHE_EXPIRY_SECONDS = os.environ.get("CACHE_EXPIRY_SECONDS", 300)
CLEANUP_INTERVAL_SECONDS = os.environ.get("CLEANUP_INTERVAL_SECONDS", 300)
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "D7qDkRjNCFu-5ylF98LsczfzpoBfvXjBRqTW1ug6stU=")

@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    connection_pool = await init_db(DATABASE_URL)
    cache_manager = CacheManager()
    fernet = Fernet(key=ENCRYPTION_KEY.encode())
    secret_router = SecretRouter(cache_manager, fernet, connection_pool)
    app.include_router(secret_router.fastapi_router)
    asyncio.create_task(cleanup_expired_data(CLEANUP_INTERVAL_SECONDS, connection_pool,
                                             cache_manager, int(CACHE_EXPIRY_SECONDS)))
    yield
    await connection_pool.close()

app = fastapi.FastAPI(lifespan=lifespan)

@app.router.get('/', include_in_schema=False)
def index() -> fastapi.responses.RedirectResponse:
    return fastapi.responses.RedirectResponse('/docs')

@app.middleware("http")
async def disable_client_cache_headers(request: fastapi.Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    uvicorn.run("main:app", reload=False, host='127.0.0.1')
