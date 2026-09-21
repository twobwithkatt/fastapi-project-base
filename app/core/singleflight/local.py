import asyncio
import threading
from typing import Any, Callable, Dict, Optional


class _Call:
    """Represents an ongoing in-flight async function call."""
    def __init__(self):
        self.future: asyncio.Future = asyncio.get_running_loop().create_future()
        self.waiters: int = 0


class AsyncLocalSingleFlight:
    """
    In-memory SingleFlight for asynchronous coroutines (within 1 Pod/Process).
    Collapses multiple concurrent calls for the same key into a single invocation.
    """
    def __init__(self):
        self._calls: Dict[str, _Call] = {}
        self._lock: Optional[asyncio.Lock] = None
        self._loop = None

    def _get_lock(self) -> asyncio.Lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if self._lock is None or self._loop != loop:
            self._lock = asyncio.Lock()
            self._loop = loop
            self._calls.clear()
        return self._lock

    async def do(self, key: str, fn: Callable, *args, **kwargs) -> Any:
        lock = self._get_lock()
        async with lock:
            if key in self._calls:
                call = self._calls[key]
                call.waiters += 1
                need_wait = True
            else:
                call = _Call()
                call.waiters = 1
                self._calls[key] = call
                need_wait = False

        if need_wait:
            return await asyncio.shield(call.future)

        # First caller (Leader in this process): execute the function
        try:
            if asyncio.iscoroutinefunction(fn):
                res = await fn(*args, **kwargs)
            else:
                res = fn(*args, **kwargs)
            call.future.set_result(res)
            return res
        except Exception as e:
            call.future.set_exception(e)
            raise e
        finally:
            lock = self._get_lock()
            async with lock:
                self._calls.pop(key, None)



class _SyncCall:
    """Represents an ongoing in-flight synchronous function call across threads."""
    def __init__(self):
        self.event = threading.Event()
        self.result: Any = None
        self.exception: Optional[Exception] = None
        self.waiters: int = 0


class SyncLocalSingleFlight:
    """
    In-memory SingleFlight for synchronous threads (within 1 Pod/Process).
    Collapses multiple concurrent thread calls for the same key into a single invocation.
    """
    def __init__(self):
        self._calls: Dict[str, _SyncCall] = {}
        self._lock = threading.Lock()

    def do(self, key: str, fn: Callable, *args, **kwargs) -> Any:
        with self._lock:
            if key in self._calls:
                call = self._calls[key]
                call.waiters += 1
                need_wait = True
            else:
                call = _SyncCall()
                call.waiters = 1
                self._calls[key] = call
                need_wait = False

        if need_wait:
            call.event.wait()
            if call.exception:
                raise call.exception
            return call.result

        try:
            res = fn(*args, **kwargs)
            call.result = res
            return res
        except Exception as e:
            call.exception = e
            raise e
        finally:
            call.event.set()
            with self._lock:
                self._calls.pop(key, None)
