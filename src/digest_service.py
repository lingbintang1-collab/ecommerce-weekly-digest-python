"""Order digest workflow: schedule, queue, then deliver one email."""
import json
import os
import smtplib
from email.message import EmailMessage
from typing import Iterable

try:
    from .infrai_client import InfraiClient
except ImportError:
    from infrai_client import InfraiClient


def digest_lines(orders: Iterable[dict]) -> list[str]:
    return [f"{order['order_id']}: {order['status']} (${order['total']:.2f})" for order in orders]


def schedule_digest(client: InfraiClient, task_url: str) -> str:
    result = client.create_cron("0 9 * * 1", task_url, "weekly-order-digest")
    return result["job_id"]


def publish_digest(client: InfraiClient, subscriber: str, orders: list[dict]) -> dict:
    payload = {"to": subscriber, "subject": "Your weekly order digest", "lines": digest_lines(orders)}
    return client.publish(payload, "digest-" + subscriber)


def send_email(payload: dict) -> None:
    message = EmailMessage()
    message["From"] = os.environ["DIGEST_FROM"]
    message["To"] = payload["to"]
    message["Subject"] = payload["subject"]
    message.set_content("\n".join(payload["lines"]))
    with smtplib.SMTP(os.environ.get("SMTP_HOST", "localhost"), int(os.environ.get("SMTP_PORT", "25"))) as smtp:
        smtp.send_message(message)


def run_worker(client: InfraiClient) -> int:
    batch = client.consume(10, 60)
    messages = batch.get("messages", [])
    for message in messages:
        send_email(message["payload"])
        client.ack(message["message_id"], "ack-" + message["message_id"])
    return len(messages)


if __name__ == "__main__":
    client = InfraiClient()
    client.create_queue("order-digests", "queue-order-digests")
    print(json.dumps({"scheduled_job": schedule_digest(client, os.environ["DIGEST_TASK_URL"])}))
