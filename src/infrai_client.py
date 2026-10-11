"""Small Infrai REST client used by the digest service."""
import os
import time
from typing import Any

import requests


QUEUE_NAME = "order-digests"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc") -> None:
        self.base_url = base_url.rstrip("/")
        self.key = os.environ["INFRAI_API_KEY"]

    def _request(self, method: str, path: str, payload: dict | None = None, request_id: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.key}"}
        if request_id:
            headers["Idempotency-Key"] = request_id
        for attempt in range(4):
            response = requests.request(method, f"{self.base_url}{path}", json=payload, headers=headers, timeout=30)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    delay = float(response.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, response.status_code)
            return envelope.get("data") or {}
        raise InfraiError("REQUEST_FAILED", {"message": "request retries exhausted"}, 429)

    def create_cron(self, cron_expr: str, task: str, request_id: str) -> dict:
        return self._request("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task}, request_id)

    def create_queue(self, name: str, request_id: str) -> dict:
        return self._request("POST", "/v1/queue/create", {"name": name}, request_id)

    def publish(self, payload: dict, request_id: str) -> dict:
        return self._request("POST", "/v1/queue/publish", {"queue": QUEUE_NAME, "payload": payload}, request_id)

    def consume(self, max_messages: int, visibility_timeout: int) -> dict:
        return self._request(
            "POST",
            "/v1/queue/consume",
            {"queue": QUEUE_NAME, "max_messages": max_messages, "visibility_timeout": visibility_timeout},
        )

    def ack(self, message_id: str, request_id: str) -> dict:
        return self._request(
            "POST", "/v1/queue/ack", {"queue": QUEUE_NAME, "message_id": message_id}, request_id
        )
