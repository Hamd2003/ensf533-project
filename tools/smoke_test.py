"""Post-deploy smoke test for all Function URLs (used by deploy.yml).

Reads the stack outputs JSON (aws cloudformation describe-stacks ... --query
"Stacks[0].Outputs") from stdin, masks every URL in the GitHub Actions log
before doing anything else, then sends the standard POST body to each one.

Reports pass/fail per function name only; URLs are never printed.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_KEY = re.compile(r"^Url(Api|Cpu|Data)(\d+)$")
ATTEMPTS = 3  # permissions on a brand-new URL can take a few seconds to apply


def post(url, body):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def check(url, workload, memory, config):
    """Return None on success, or a short reason for the failure."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            status, raw = post(url, config["request_body"])
        except (urllib.error.URLError, TimeoutError) as exc:
            status, raw = None, str(exc).encode()
        if status == 200:
            break
        if attempt < ATTEMPTS:
            time.sleep(5)
    if status != 200:
        return f"HTTP {status}"

    try:
        body = json.loads(raw)
    except ValueError:
        return "response is not JSON"
    if body.get("ok") is not True:
        return "ok != true"
    if body.get("workload") != workload:
        return f"workload {body.get('workload')!r} != {workload!r}"
    if body.get("memory_mb") != memory:
        return f"memory_mb {body.get('memory_mb')} != {memory}"
    expected = config.get("expected_results", {}).get(workload)
    if expected is not None and body.get("result") != expected:
        return "result differs from expected_results"
    return None


def main():
    outputs = json.load(sys.stdin) or []
    urls = {o["OutputKey"]: o["OutputValue"] for o in outputs if OUTPUT_KEY.match(o["OutputKey"])}
    # Mask first, so nothing printed afterwards can reveal a URL.
    for url in urls.values():
        print(f"::add-mask::{url}", flush=True)

    config = json.loads((ROOT / "config" / "experiment.json").read_text())
    expected_cells = {
        f"Url{w.capitalize()}{m}" for w in config["workloads"] for m in config["memory_levels_mb"]
    }

    rows, failures = [], 0
    for key in sorted(expected_cells | set(urls)):
        workload, memory = OUTPUT_KEY.match(key).groups()
        workload, memory = workload.lower(), int(memory)
        name = f"seng533-{workload}-{memory}"
        reason = "missing stack output" if key not in urls else check(urls[key], workload, memory, config)
        failures += reason is not None
        rows.append(f"| `{name}` | {'pass' if reason is None else 'FAIL: ' + reason} |")
        print(f"{name}: {'pass' if reason is None else 'FAIL (' + reason + ')'}", flush=True)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("### Smoke test\n\n| Function | Result |\n|---|---|\n" + "\n".join(rows) + "\n")

    if failures:
        sys.exit(f"{failures} function(s) failed the smoke test")


if __name__ == "__main__":
    main()
