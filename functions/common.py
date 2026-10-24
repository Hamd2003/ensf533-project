"""Shared request handling and response contract for all workloads.

Every handler delegates to `handle()`, which rejects non-POST requests, parses
the JSON body, times the workload with perf_counter and wraps the result in the
response contract (see docs/load-test-interface.md).

No per-request logging on purpose: it adds latency, and the platform REPORT
line already gives duration, billed duration, memory and init duration.
"""

import base64
import json
import time
import uuid

# One id per execution environment (module import = environment init).
ENV_ID = uuid.uuid4().hex
_invocations = 0


class BadRequest(Exception):
    """Raised by a workload when the request body fails validation (HTTP 400)."""


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, separators=(",", ":")),
    }


def _parse_body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    if not raw:
        return {}
    return json.loads(raw)


def handle(event, context, workload, compute):
    """Run `compute(payload)` for a Function URL event (payload format 2.0)."""
    global _invocations
    _invocations += 1
    cold = _invocations == 1
    memory_mb = int(context.memory_limit_in_mb)

    def error(status, message):
        return _response(status, {
            "ok": False,
            "workload": workload,
            "memory_mb": memory_mb,
            "error": message,
        })

    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    if method != "POST":
        return error(405, "method not allowed")

    try:
        payload = _parse_body(event)
    except (ValueError, UnicodeDecodeError):
        return error(400, "body is not valid JSON")

    start = time.perf_counter()
    try:
        result = compute(payload)
    except BadRequest as exc:
        return error(400, str(exc))
    compute_ms = (time.perf_counter() - start) * 1000.0

    return _response(200, {
        "ok": True,
        "workload": workload,
        "memory_mb": memory_mb,
        "result": result,
        "compute_ms": round(compute_ms, 3),
        "env_id": ENV_ID,
        "cold": cold,
    })
