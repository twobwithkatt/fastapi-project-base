import redis
import redis.asyncio as aioredis
import json
from typing import Optional
from app.core.config import settings

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            db=0,
        )

    def get_json(self, key):
        data = self.client.get(key)
        return json.loads(data) if data else None


    def set_with_ttl(self, key, value, ttl=None):
        self.client.set(key, value, ex=ttl)


    def delete(self, key):
        self.client.delete(key)

    
    def get_key(self, key):
        return self.client.get(key)

redis_client = RedisClient()

def get_redis() -> RedisClient:
    return redis_client


_async_redis: Optional[aioredis.Redis] = None
_async_redis_loop = None

def get_async_redis() -> aioredis.Redis:
    global _async_redis, _async_redis_loop
    try:
        import asyncio
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _async_redis is None or _async_redis_loop != current_loop:
        _async_redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            db=0,
        )
        _async_redis_loop = current_loop
    return _async_redis


