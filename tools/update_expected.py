"""Recompute `expected_results` in config/experiment.json from the handlers.

Run after changing prime_limit, dataset_size or dataset_seed (pilot calibration):

    python3 tools/update_expected.py

Refuses to run once the config is frozen, since changing workload sizes then
invalidates every run so far.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "experiment.json"


class _Context:
    memory_limit_in_mb = "0"


def main():
    config = json.loads(CONFIG.read_text())
    if config.get("frozen"):
        sys.exit("experiment.json is frozen; unfreeze it deliberately before changing workload sizes")

    os.environ["PRIME_LIMIT"] = str(config["prime_limit"])
    os.environ["DATASET_SIZE"] = str(config["dataset_size"])
    os.environ["DATASET_SEED"] = str(config["dataset_seed"])
    sys.path.insert(0, str(ROOT / "functions"))
    import api, cpu, data  

    event = {
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps(config["request_body"]),
        "isBase64Encoded": False,
    }
    expected = {}
    for module in (api, cpu, data):
        body = json.loads(module.handler(event, _Context())["body"])
        expected[module.WORKLOAD] = body["result"]

    config["expected_results"] = expected
    CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    print(json.dumps(expected, indent=2))


if __name__ == "__main__":
    main()
