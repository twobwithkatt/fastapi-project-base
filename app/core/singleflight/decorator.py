import functools
import inspect
from typing import Any, Callable, Optional, Union

from app.core.singleflight.distributed import (
    AsyncDistributedSingleFlight,
    SyncDistributedSingleFlight,
)
from app.db.redis import get_async_redis, get_redis

_default_async_flight: Optional[AsyncDistributedSingleFlight] = None
_default_sync_flight: Optional[SyncDistributedSingleFlight] = None


def get_default_async_singleflight() -> AsyncDistributedSingleFlight:
    global _default_async_flight
    client = get_async_redis()
    if _default_async_flight is None or _default_async_flight.redis != client:
        _default_async_flight = AsyncDistributedSingleFlight(
            redis_client=client,
        )
    return _default_async_flight



def get_default_sync_singleflight() -> SyncDistributedSingleFlight:
    global _default_sync_flight
    if _default_sync_flight is None:
        _default_sync_flight = SyncDistributedSingleFlight(
            redis_client=get_redis().client,
        )
    return _default_sync_flight


def distributed_singleflight(
    key_pattern: Optional[str] = None,
    key_maker: Optional[Callable[..., str]] = None,
    cache_ttl: int = 60,
    lock_ttl_ms: int = 10000,
    wait_timeout_s: float = 5.0,
):
    """
    Decorator to wrap async or sync functions with Two-Tier Distributed Singleflight.
    
    Usage:
        @distributed_singleflight(key_pattern="post:{post_id}", cache_ttl=30)
        async def get_post_by_id(post_id: int):
            ...
    """

    def decorator(func: Callable):
        sig = inspect.signature(func)
        is_async = inspect.iscoroutinefunction(func)

        def _resolve_key(*args, **kwargs) -> str:
            if key_maker:
                return key_maker(*args, **kwargs)
            
            if key_pattern:
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                # Exclude self/cls if formatting
                format_kwargs = {
                    k: v for k, v in bound_args.arguments.items()
                    if k not in ("self", "cls")
                }
                return key_pattern.format(**format_kwargs)
            
            # Default fallback key: module:func_name:args
            arg_str = "_".join(str(a) for a in args if not hasattr(a, "__dict__"))
            kw_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            return f"{func.__module__}:{func.__name__}:{arg_str}:{kw_str}"

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                key = _resolve_key(*args, **kwargs)
                flight = get_default_async_singleflight()
                return await flight.execute(
                    key,
                    func,
                    cache_ttl,
                    *args,
                    **kwargs,
                )
            return async_wrapper

        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                key = _resolve_key(*args, **kwargs)
                flight = get_default_sync_singleflight()
                return flight.execute(
                    key,
                    func,
                    cache_ttl,
                    *args,
                    **kwargs,
                )
            return sync_wrapper


    return decorator
