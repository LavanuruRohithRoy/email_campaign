from __future__ import annotations

import asyncio
import pytest

from app.workers.send_worker import handle_message_with_retries
from app.config import settings


class SimpleFakeRedis:
    def __init__(self):
        self.store = {}
        self.exp = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.exp[key] = seconds


class DummyMessage(dict):
    pass


@pytest.mark.asyncio
async def test_retry_and_dlq(monkeypatch):
    # Simulate process_send_message raising to trigger retries
    calls = {"dlq": 0, "deleted": 0}

    async def fake_process(msg, db=None):
        raise RuntimeError("simulated failure")

    async def fake_send_to_dlq(dlq_url, body):
        calls["dlq"] += 1

    async def fake_delete(queue_url, receipt):
        calls["deleted"] += 1

    monkeypatch.setattr("app.workers.send_worker.process_send_message", fake_process)
    monkeypatch.setattr("app.utils.ses.send_message_to_dlq", fake_send_to_dlq)
    monkeypatch.setattr("app.utils.ses.delete_sqs_message", fake_delete)

    fake_redis = SimpleFakeRedis()

    msg = {"receipt_handle": "rh-1", "body": {"campaign_id": "c1", "contact_id": "u1"}}

    # Call handler WORKER_MAX_RETRIES + 1 times to force DLQ
    for _ in range(settings.WORKER_MAX_RETRIES + 1):
        # patch asyncio.sleep to avoid slow tests
        monkeypatch.setattr(asyncio, "sleep", lambda *_args, **_kwargs: asyncio.sleep(0))
        try:
            await handle_message_with_retries(msg, fake_redis)
        except Exception:
            # handler should swallow exceptions; continue
            pass

    assert calls["dlq"] == 1


@pytest.mark.asyncio
async def test_exponential_backoff(monkeypatch):
    delays = []

    async def fake_sleep(sec):
        delays.append(sec)

    async def fake_process(msg, db=None):
        raise RuntimeError("fail")

    async def fake_send_to_dlq(dlq_url, body):
        return None

    async def fake_delete(queue_url, receipt):
        return None

    monkeypatch.setattr("app.workers.send_worker.process_send_message", fake_process)
    monkeypatch.setattr("app.utils.ses.send_message_to_dlq", fake_send_to_dlq)
    monkeypatch.setattr("app.utils.ses.delete_sqs_message", fake_delete)
    import asyncio as _asyncio
    monkeypatch.setattr(_asyncio, "sleep", fake_sleep)

    fake_redis = SimpleFakeRedis()
    msg = {"receipt_handle": "rh-2", "body": {"campaign_id": "c2", "contact_id": "u2"}}

    for _ in range(3):
        await handle_message_with_retries(msg, fake_redis)

    # delays captured should show increasing backoff values
    assert len(delays) >= 3
    assert delays[0] >= 1
    assert delays[1] >= delays[0]
