"""Optional RocketMQ consumer.

If the `rocketmq-client-python` package is installed, this module can consume
diagnosis tasks directly from RocketMQ. Otherwise the runtime falls back to the
Control Plane polling consumer in `consumer.py`.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable

from app.idempotency import IdempotencyStore

try:
    from rocketmq.client import ConsumeStatus, MessageListener, PushConsumer
    ROCKETMQ_AVAILABLE = True
except Exception:  # pragma: no cover
    ROCKETMQ_AVAILABLE = False


class _Listener(MessageListener):
    def __init__(self, handler: Callable[[dict[str, Any]], None],
                 idempotency_store: IdempotencyStore | None = None):
        self.handler = handler
        self.idempotency_store = idempotency_store

    def consume_message(self, msg):
        body = msg.body.decode("utf-8") if isinstance(msg.body, bytes) else str(msg.body)
        try:
            payload = json.loads(body)
            event_id = payload.get("eventId") or payload.get("taskId")
            if self.idempotency_store is not None and event_id:
                if self.idempotency_store.is_processed(str(event_id)):
                    return ConsumeStatus.CONSUME_SUCCESS
            self.handler({"body": body, "payload": payload})
            if self.idempotency_store is not None and event_id:
                self.idempotency_store.mark_processed(str(event_id))
            return ConsumeStatus.CONSUME_SUCCESS
        except Exception:
            return ConsumeStatus.RECONSUME_LATER


def start_rocketmq_consumer(handler: Callable[[dict[str, Any]], None],
                            name_server: str | None = None,
                            topic: str = "aisre-agent-task",
                            group: str = "aisre-agent-runtime",
                            idempotency_store: IdempotencyStore | None = None):
    if not ROCKETMQ_AVAILABLE:
        return None
    consumer = PushConsumer(group)
    consumer.set_namesrv_addr(name_server or os.getenv("ROCKETMQ_NAME_SERVER", "localhost:9876"))
    consumer.subscribe(topic, _Listener(handler, idempotency_store))
    consumer.start()
    return consumer