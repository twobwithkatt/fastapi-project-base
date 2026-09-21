import asyncio
import time
from unittest.mock import MagicMock, AsyncMock
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
import redis

from app.core.config import settings
from app.core.singleflight.local import AsyncLocalSingleFlight, SyncLocalSingleFlight
from app.core.singleflight.distributed import (
    AsyncDistributedSingleFlight,
    SyncDistributedSingleFlight,
)
from app.core.singleflight.decorator import distributed_singleflight


@pytest.fixture
def redis_async_client():
    client = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    yield client
    # In pytest teardown, we close the client
    # Note: client.aclose() in asyncio fixture if async


@pytest.fixture
def redis_sync_client():
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    yield client
    client.close()


@pytest.mark.asyncio
async def test_async_local_singleflight():
    """Kiểm tra Local Singleflight: 500 coroutines đồng thời chỉ gọi hàm gốc đúng 1 lần."""
    sf = AsyncLocalSingleFlight()
    call_count = 0

    async def expensive_query(query_id: int):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)  # Giả lập query DB tốn 50ms
        return f"result_{query_id}"

    # Bắn 500 coroutines cùng lúc với cùng 1 key
    tasks = [sf.do("query_1", expensive_query, 1) for _ in range(500)]
    results = await asyncio.gather(*tasks)

    assert call_count == 1, f"Expected 1 call, but got {call_count}"
    assert len(results) == 500
    assert all(r == "result_1" for r in results)


def test_sync_local_singleflight():
    """Kiểm tra Sync Local Singleflight: 50 threads đồng thời chỉ gọi hàm gốc đúng 1 lần."""
    import concurrent.futures

    sf = SyncLocalSingleFlight()
    call_count = 0

    def expensive_query(query_id: int):
        nonlocal call_count
        call_count += 1
        time.sleep(0.05)
        return f"result_{query_id}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [
            executor.submit(sf.do, "query_sync_1", expensive_query, 1)
            for _ in range(50)
        ]
        results = [f.result() for f in futures]

    assert call_count == 1
    assert len(results) == 50
    assert all(r == "result_1" for r in results)


@pytest.mark.asyncio
async def test_distributed_singleflight_multi_pod_simulation():
    """
    Giả lập 5 Pod khác nhau (5 instance AsyncDistributedSingleFlight riêng biệt)
    cùng kết nối vào Redis.
    Bắn 500 requests phân bổ ngẫu nhiên trên cả 5 Pods vào cùng một key vừa hết hạn cache.
    Kỳ vọng:
    - Hàm Database (origin) CHỈ được gọi ĐÚNG 1 LẦN duy nhất trên toàn cụm.
    - Cả 500 requests trên cả 5 Pods đều nhận kết quả hợp lệ.
    """
    client = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )

    test_key = "product_hot_sale_99"
    # Dọn dẹp cache và lock trước khi test
    await client.delete(f"cache:sf:{test_key}")
    await client.delete(f"lock:sf:{test_key}")

    # Tạo 5 Pods giả lập
    pods = [
        AsyncDistributedSingleFlight(redis_client=client)
        for _ in range(5)
    ]

    db_call_count = 0

    async def fetch_from_db(item_id: str):
        nonlocal db_call_count
        db_call_count += 1
        await asyncio.sleep(0.1)  # Giả lập query DB nặng 100ms
        return {"item_id": item_id, "name": "iPhone 16 Pro Max", "price": 1000}

    # Chia 500 requests ngẫu nhiên vào 5 Pods
    import random
    tasks = []
    for _ in range(500):
        selected_pod = random.choice(pods)
        tasks.append(
            selected_pod.execute(
                key=test_key,
                fetch_fn=fetch_from_db,
                cache_ttl=60,
                item_id="99",
            )
        )

    results = await asyncio.gather(*tasks)

    # ĐÚNG 1 query DB duy nhất
    assert db_call_count == 1, f"DB must be called exactly once, but was called {db_call_count} times!"
    assert len(results) == 500
    for res in results:
        assert res["name"] == "iPhone 16 Pro Max"
        assert res["price"] == 1000

    # Kiểm tra data đã được ghi vào Redis cache
    cached = await client.get(f"cache:sf:{test_key}")
    assert cached is not None
    assert "iPhone 16 Pro Max" in cached

    # Cleanup
    await client.delete(f"cache:sf:{test_key}")
    await client.aclose()


@pytest.mark.asyncio
async def test_decorator_distributed_singleflight():
    """Kiểm tra @distributed_singleflight decorator hoạt động chính xác."""
    db_calls = 0

    @distributed_singleflight(key_pattern="order:{order_id}", cache_ttl=30)
    async def get_order_detail(order_id: int):
        nonlocal db_calls
        db_calls += 1
        await asyncio.sleep(0.05)
        return {"order_id": order_id, "status": "completed"}

    # Xóa cache
    client = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    await client.delete("cache:sf:order:123")

    tasks = [get_order_detail(123) for _ in range(100)]
    results = await asyncio.gather(*tasks)

    assert db_calls == 1
    assert len(results) == 100
    assert all(r["order_id"] == 123 for r in results)

    await client.delete("cache:sf:order:123")
    await client.aclose()


def test_sync_distributed_singleflight_simulation():
    """Kiểm tra SyncDistributedSingleFlight hoạt động đa luồng và đa pod giả lập."""
    import concurrent.futures

    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    test_key = "sync_inventory_check_456"
    client.delete(f"cache:sf:{test_key}")
    client.delete(f"lock:sf:{test_key}")

    # 3 Pods đồng bộ
    pods = [
        SyncDistributedSingleFlight(redis_client=client)
        for _ in range(3)
    ]

    db_call_count = 0

    def query_inventory(item_id: int):
        nonlocal db_call_count
        db_call_count += 1
        time.sleep(0.08)
        return {"item_id": item_id, "stock": 42}

    import random
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = [
            executor.submit(
                random.choice(pods).execute,
                test_key,
                query_inventory,
                60,
                456,
            )
            for _ in range(30)
        ]
        results = [f.result() for f in futures]

    assert db_call_count == 1, f"Expected 1 DB call, got {db_call_count}"
    assert len(results) == 30
    assert all(r["stock"] == 42 for r in results)

    client.delete(f"cache:sf:{test_key}")
    client.close()


@pytest.mark.asyncio
async def test_cache_null_prevents_penetration():
    """Kiểm tra Cache Penetration: Khi query không tồn tại (None), cache sentinel được lưu và không gọi DB lại."""
    client = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    test_key = "non_existent_item_999"
    await client.delete(f"cache:sf:{test_key}")
    await client.delete(f"lock:sf:{test_key}")

    pod = AsyncDistributedSingleFlight(redis_client=client, cache_null=True, null_ttl_s=5)
    db_calls = 0

    async def fetch_missing():
        nonlocal db_calls
        db_calls += 1
        return None

    # Lần 1: 50 requests đồng thời
    tasks = [pod.execute(test_key, fetch_missing) for _ in range(50)]
    results = await asyncio.gather(*tasks)

    assert db_calls == 1
    assert all(r is None for r in results)

    # Lần 2: 50 requests tiếp theo phải ăn cache sentinel và KHÔNG gọi DB thêm lần nào
    tasks2 = [pod.execute(test_key, fetch_missing) for _ in range(50)]
    results2 = await asyncio.gather(*tasks2)

    assert db_calls == 1  # Vẫn là 1!
    assert all(r is None for r in results2)

    await client.delete(f"cache:sf:{test_key}")
    await client.aclose()


@pytest.mark.asyncio
async def test_follower_failover_when_leader_times_out():
    """
    Kiểm tra khả năng chịu lỗi (Fail-safe):
    Nếu Leader Pod bị sự cố và lock hết hạn mà chưa kịp set cache,
    Follower Pod sau khi timeout sẽ tự động tranh lock mới và query thành công,
    không làm treo hay hủy request của người dùng.
    """
    client = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    test_key = "failover_test_key"
    await client.delete(f"cache:sf:{test_key}")
    await client.delete(f"lock:sf:{test_key}")

    # Giả lập lock của một "Leader" bị chết trước đó, lock hết hạn sau 300ms
    await client.set(f"lock:sf:{test_key}", "dead_pod_token", px=300)

    # Follower Pod với timeout 0.4s
    follower_pod = AsyncDistributedSingleFlight(
        redis_client=client,
        lock_ttl_ms=2000,
        wait_timeout_s=0.4,
    )

    db_calls = 0
    async def fallback_fetch():
        nonlocal db_calls
        db_calls += 1
        return {"status": "recovered"}

    # Follower vào, thấy lock có sẵn, chờ đợi.
    # Sau 0.4s (lock của dead pod đã hết hạn lúc 300ms), Follower retry và giành lock để fetch!
    result = await follower_pod.execute(test_key, fallback_fetch)

    assert result == {"status": "recovered"}
    assert db_calls == 1

    await client.delete(f"cache:sf:{test_key}")
    await client.aclose()

