from datetime import datetime, timedelta
from typing import Dict, Optional, Union
from src.database.models import SecretCache, Secret

class CacheManager:
    def __init__(self):
        self._cache: Dict[str, SecretCache] = {}

    async def create_secret_cache(self, key: str, secret: SecretCache):
        self._cache[key] = secret

    async def get_secret_value(self, secret_key: str, passphrase: str) -> Optional[Union[str, int]]:
        if secret_key in self._cache:
            secret: SecretCache = self._cache[secret_key]
            secret_ttl = secret.ttl_seconds
            if secret.passphrase is not None and passphrase != secret.passphrase:
                return 403
            if secret_ttl is not None:
                if datetime.utcnow() - secret.created_at >= timedelta(seconds=secret.ttl_seconds):
                    await self.delete_secret(secret_key, secret.passphrase)
                    return 410
            await self.delete_secret(secret_key, secret.passphrase)
            return secret.value
        return None

    async def delete_secret(self, secret_key: str, passphrase: str = None):
        if secret_key in self._cache:
            secret: SecretCache = self._cache[secret_key]
            if secret.passphrase is not None and passphrase != secret.passphrase:
                return
            del self._cache[secret_key]

    async def clean_expired_cache(self, cache_lifetime: int) -> int:
        keys_to_delete = []
        for key, value in self._cache.items():
            if datetime.utcnow() - value.created_at >= timedelta(seconds=cache_lifetime):
                keys_to_delete.append(key)
        count = len(keys_to_delete)
        for key in keys_to_delete:
            del self._cache[key]
        return count
