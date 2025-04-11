from typing import Optional, Union
from datetime import datetime
from pydantic import BaseModel

class Secret(BaseModel):
    value: Union[str, bytes]
    passphrase: Optional[str] = None
    ttl_seconds: Optional[int] = None

class SecretCache(Secret):
    created_at: datetime
