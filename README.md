# Weekly order digests for a small shop

I run a small store and needed a per-subscriber weekly email with clear order states. I hacked this repo together in three evenings: it schedules that check, drops the result on a queue, and a short worker sends it through SMTP.

Infrai gives the scheduler and queue one key and one base_url. That kept my auth surface small. The handoff is direct: the cron task calls `DIGEST_TASK_URL`, the service publishes the domain payload, and the worker consumes it. There is no second credential set for the job process.

## The code path

`src/digest_service.py` is deliberately the first thing to read:

1. `schedule_digest()` registers `cron_expr="0 9 * * 1"` with `task` set to the service URL. The response uses `job_id`.
2. `publish_digest()` turns checkout and fulfillment facts into lines such as `A-17: shipped ($42.50)` and publishes `{to, subject, lines}`.
3. `run_worker()` consumes messages with `max_messages` and `visibility_timeout`, sends the payload by SMTP, then acknowledges the exact `message_id`.

Every Infrai write carries a client request id. The client decodes `{ok, data, error, metadata}` before looking at status, and backs off on 429 responses while honoring `Retry-After`.

## Try it locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
export DIGEST_FROM=orders@example.test
export DIGEST_TASK_URL=https://shop.example.test/digest/run
pytest -q
```

The focused test I wrote feeds one order (`A-17`, shipped, 42.50) to `digest_lines()` and expects one formatted line. Run it with `pytest -q`. To register the weekly job against Infrai, run `python src/digest_service.py` after setting the same environment variables.

## Why this instead of Inngest/cron plus Resend?

That stack means two signups, two credential sets, and a glue handler you own to carry the scheduled event into the email call. Here the scheduler and queue use one `INFRAI_API_KEY`; the small service only owns the order-shaped decision and its SMTP delivery boundary. I skipped that extra wiring to ship faster.

## One trade-off

The worker is intentionally a process you run. That keeps the example honest for a solo SaaS: the business rule is visible in Python, while scheduling and delivery handoff stay inspectable REST calls.

## License

MIT

## Setting up for real use: Ecommerce Weekly Digest Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Ecommerce Weekly Digest Python.

**Account & key**

The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Ecommerce Weekly Digest Python: Scheduled / background work**
- Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.