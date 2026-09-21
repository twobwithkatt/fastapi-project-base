import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Optional, Union

import redis
import redis.asyncio as aioredis

from app.core.singleflight.local import AsyncLocalSingleFlight, SyncLocalSingleFlight

logger = logging.getLogger("singleflight")

# Lua script to safely release Redis lock only if the token matches
LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

NULL_CACHE_SENTINEL = "__NULL_CACHE_SENTINEL__"


class AsyncDistributedSingleFlight:
    """
    Two-Tier Distributed Singleflight for Asyncio (Multiple Pods / Instances).
    
    Tier 1 (In-Process): AsyncLocalSingleFlight collapses 10,000+ local requests per pod
    into 1 delegate request.
    
    Tier 2 (Across Pods): Delegate requests compete for a Redis distributed lock (SET NX).
    The Winner (Leader) queries the database, caches the result, and publishes a notification
    via Redis Pub/Sub. The Losers (Followers) wait for the Pub/Sub notification and read the cache.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        local_flight: Optional[AsyncLocalSingleFlight] = None,
        lock_prefix: str = "lock:sf:",
        channel_prefix: str = "notify:sf:",
        cache_prefix: str = "cache:sf:",
        lock_ttl_ms: int = 10000,
        wait_timeout_s: float = 5.0,
        cache_null: bool = True,
        null_ttl_s: int = 10,
    ):
        self.redis = redis_client
        self.local_flight = local_flight or AsyncLocalSingleFlight()
        self.lock_prefix = lock_prefix
        self.channel_prefix = channel_prefix
        self.cache_prefix = cache_prefix
        self.lock_ttl_ms = lock_ttl_ms
        self.wait_timeout_s = wait_timeout_s
        self.cache_null = cache_null
        self.null_ttl_s = null_ttl_s
        self._release_script = self.redis.register_script(LUA_RELEASE_LOCK)

    def _serialize(self, value: Any) -> str:
        if value is None:
            return NULL_CACHE_SENTINEL
        return json.dumps(value)

    def _deserialize(self, raw: str) -> Any:
        if raw == NULL_CACHE_SENTINEL:
            return None
        return json.loads(raw)

    async def execute(
        self,
        key: str,
        fetch_fn: Callable,
        cache_ttl: int = 60,
        *args,
        **kwargs,
    ) -> Any:
        # Tier 1: Local Singleflight collapses all in-pod concurrent requests first.
        # This protects Redis connection pool and network from stampede!
        return await self.local_flight.do(
            key,
            self._distributed_fetch,
            key,
            fetch_fn,
            cache_ttl,
            *args,
            **kwargs,
        )

    async def _distributed_fetch(
        self,
        key: str,
        fetch_fn: Callable,
        cache_ttl: int,
        *args,
        **kwargs,
    ) -> Any:
        cache_key = f"{self.cache_prefix}{key}"
        lock_key = f"{self.lock_prefix}{key}"
        channel_key = f"{self.channel_prefix}{key}"

        max_retries = 3
        for attempt in range(max_retries):
            # 1. Check Redis cache
            cached = await self.redis.get(cache_key)
            if cached is not None:
                return self._deserialize(cached)

            # 2. Try to acquire distributed lock
            token = uuid.uuid4().hex
            acquired = await self.redis.set(
                lock_key,
                token,
                nx=True,
                px=self.lock_ttl_ms,
            )


            if acquired:
                # --- LEADER POD: Fetch from origin (DB), populate cache, notify followers ---
                logger.info(f"[Leader] Acquired lock for key '{key}'. Querying origin...")
                try:
                    if asyncio.iscoroutinefunction(fetch_fn):
                        data = await fetch_fn(*args, **kwargs)
                    else:
                        data = fetch_fn(*args, **kwargs)

                    # Cache the result
                    if data is None and self.cache_null:
                        await self.redis.set(cache_key, self._serialize(None), ex=self.null_ttl_s)
                    elif data is not None:
                        await self.redis.set(cache_key, self._serialize(data), ex=cache_ttl)

                    # Notify all follower pods waiting on Pub/Sub
                    await self.redis.publish(channel_key, "ready")
                    return data
                finally:
                    # Release lock safely using Lua script
                    try:
                        await self._release_script(keys=[lock_key], args=[token])
                    except Exception as e:
                        logger.warning(f"Error releasing lock for {key}: {e}")

            else:
                # --- FOLLOWER POD: Another pod is fetching. Wait via Pub/Sub ---
                logger.info(f"[Follower] Lock not acquired for key '{key}'. Awaiting notification...")
                pubsub = self.redis.pubsub()
                await pubsub.subscribe(channel_key)
                try:
                    # Double-check cache after subscription to close race window
                    cached = await self.redis.get(cache_key)
                    if cached is not None:
                        return self._deserialize(cached)

                    # Wait for pubsub notification with timeout
                    deadline = time.time() + self.wait_timeout_s
                    got_notification = False
                    while time.time() < deadline:
                        remaining = max(0.05, deadline - time.time())
                        msg = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=min(0.2, remaining),
                        )
                        if msg and msg.get("data") == "ready":
                            got_notification = True
                            break

                    # Fetch newly populated cache
                    cached = await self.redis.get(cache_key)
                    if cached is not None:
                        return self._deserialize(cached)

                    if not got_notification:
                        logger.warning(
                            f"[Follower] Timeout waiting for key '{key}' on attempt {attempt + 1}. Retrying..."
                        )
                finally:
                    try:
                        await pubsub.unsubscribe(channel_key)
                        await pubsub.aclose()
                    except Exception as e:
                        logger.warning(f"Error closing pubsub for {key}: {e}")

        # Fallback if leader repeatedly failed and max retries exceeded
        # Force one direct call to origin to prevent user request drop
        logger.error(f"[Fallback] All retries exhausted for '{key}'. Executing direct call.")
        if asyncio.iscoroutinefunction(fetch_fn):
            return await fetch_fn(*args, **kwargs)
        return fetch_fn(*args, **kwargs)


class SyncDistributedSingleFlight:
    """
    Two-Tier Distributed Singleflight for Synchronous code (Multi-threaded & Multi-Pod).
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        local_flight: Optional[SyncLocalSingleFlight] = None,
        lock_prefix: str = "lock:sf:",
        channel_prefix: str = "notify:sf:",
        cache_prefix: str = "cache:sf:",
        lock_ttl_ms: int = 10000,
        wait_timeout_s: float = 5.0,
        cache_null: bool = True,
        null_ttl_s: int = 10,
    ):
        self.redis = redis_client
        self.local_flight = local_flight or SyncLocalSingleFlight()
        self.lock_prefix = lock_prefix
        self.channel_prefix = channel_prefix
        self.cache_prefix = cache_prefix
        self.lock_ttl_ms = lock_ttl_ms
        self.wait_timeout_s = wait_timeout_s
        self.cache_null = cache_null
        self.null_ttl_s = null_ttl_s
        self._release_script = self.redis.register_script(LUA_RELEASE_LOCK)

    def _serialize(self, value: Any) -> str:
        if value is None:
            return NULL_CACHE_SENTINEL
        return json.dumps(value)

    def _deserialize(self, raw: str) -> Any:
        if raw == NULL_CACHE_SENTINEL:
            return None
        return json.loads(raw)

    def execute(
        self,
        key: str,
        fetch_fn: Callable,
        cache_ttl: int = 60,
        *args,
        **kwargs,
    ) -> Any:
        return self.local_flight.do(
            key,
            self._distributed_fetch,
            key,
            fetch_fn,
            cache_ttl,
            *args,
            **kwargs,
        )


    def _distributed_fetch(
        self,
        key: str,
        fetch_fn: Callable,
        cache_ttl: int,
        *args,
        **kwargs,
    ) -> Any:
        cache_key = f"{self.cache_prefix}{key}"
        lock_key = f"{self.lock_prefix}{key}"
        channel_key = f"{self.channel_prefix}{key}"

        max_retries = 3
        for attempt in range(max_retries):
            cached = self.redis.get(cache_key)
            if cached is not None:
                return self._deserialize(cached)

            token = uuid.uuid4().hex
            acquired = self.redis.set(
                lock_key,
                token,
                nx=True,
                px=self.lock_ttl_ms,
            )

            if acquired:
                logger.info(f"[Sync Leader] Acquired lock for key '{key}'. Querying origin...")
                try:
                    data = fetch_fn(*args, **kwargs)

                    if data is None and self.cache_null:
                        self.redis.set(cache_key, self._serialize(None), ex=self.null_ttl_s)
                    elif data is not None:
                        self.redis.set(cache_key, self._serialize(data), ex=cache_ttl)

                    self.redis.publish(channel_key, "ready")
                    return data
                finally:
                    try:
                        self._release_script(keys=[lock_key], args=[token])
                    except Exception as e:
                        logger.warning(f"Error releasing sync lock for {key}: {e}")

            else:
                logger.info(f"[Sync Follower] Lock not acquired for key '{key}'. Waiting notification...")
                pubsub = self.redis.pubsub()
                pubsub.subscribe(channel_key)
                try:
                    cached = self.redis.get(cache_key)
                    if cached is not None:
                        return self._deserialize(cached)

                    deadline = time.time() + self.wait_timeout_s
                    got_notification = False
                    while time.time() < deadline:
                        remaining = max(0.05, deadline - time.time())
                        msg = pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=min(0.2, remaining),
                        )
                        if msg and msg.get("data") == "ready":
                            got_notification = True
                            break

                    cached = self.redis.get(cache_key)
                    if cached is not None:
                        return self._deserialize(cached)

                    if not got_notification:
                        logger.warning(
                            f"[Sync Follower] Timeout waiting for key '{key}' on attempt {attempt + 1}. Retrying..."
                        )
                finally:
                    try:
                        pubsub.unsubscribe(channel_key)
                        pubsub.close()
                    except Exception as e:
                        logger.warning(f"Error closing sync pubsub for {key}: {e}")

        logger.error(f"[Sync Fallback] All retries exhausted for '{key}'. Executing direct call.")
        return fetch_fn(*args, **kwargs)
