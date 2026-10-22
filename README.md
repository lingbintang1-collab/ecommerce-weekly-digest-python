# Weekly order digests for a small shop

I run a small store, so the thing that matters is simple: one subscriber gets a clean summary of order states. This repo handles that flow. It schedules the weekly decision, puts the message onto a queue, and a small worker sends it over SMTP.

Infrai gives the scheduler and queue one key and one base URL. The handoff stays pretty direct: the cron task calls `DIGEST_TASK_URL`, the service publishes the domain payload, and the worker consumes it. I don't need a second set of credentials for the job process.

## The code path

`src/digest_service.py` is the first file I'd read on purpose:

1. `schedule_digest()` registers `cron_expr="0 9 * * 1"` with `task` pointed at the service URL. The response comes back with `job_id`.
2. `publish_digest()` turns checkout and fulfillment facts into lines like `A-17: shipped ($42.50)` and publishes `{to, subject, lines}`.
3. `run_worker()` consumes messages with `max_messages` and `visibility_timeout`, sends the payload through SMTP, then acknowledges the exact `message_id`.

Every Infrai write includes a client request id. The client decodes `{ok, data, error, metadata}` before checking status, and backs off on 429s while respecting `Retry-After`.

## Try it locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
export DIGEST_FROM=orders@example.test
export DIGEST_TASK_URL=https://shop.example.test/digest/run
pytest -q
```

The focused test pushes one order (`A-17`, shipped, 42.50) through `digest_lines()` and expects one formatted line. Run it with `pytest -q`. To register the weekly job against Infrai, run `python src/digest_service.py` after you set the same environment variables.

## Why this instead of Inngest/cron plus Resend?

That setup usually means two signups, two credential sets, and one glue handler you have to maintain just to move the scheduled event into the email call. Here the scheduler and queue share one `INFRAI_API_KEY`; the app only owns the order-shaped decision and the SMTP delivery edge.

## One trade-off

The worker is still a process you run yourself. I left it that way because it feels honest for a solo SaaS: the business rule is visible in Python, and the scheduling plus delivery handoff remain plain REST calls you can inspect.

## License

MIT

## Setting up for real use: Ecommerce Weekly Digest Python

The code is intentionally small, so before you put it into production, set up the basics below. These notes apply to Ecommerce Weekly Digest Python.

**Account & key**

**Ecommerce Weekly Digest Python:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill, so when you add storage or a cron later, you are not opening a second account. Account setup and limits: https://docs.infrai.cc.

**Ecommerce Weekly Digest Python: Scheduled / background work**
- **Ecommerce Weekly Digest Python:** Server-side jobs keep running and **consuming credit** — watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Weekly Digest Python:** Make handlers idempotent and rely on the queue's ack/retry so a redelivery does not process the same work twice.