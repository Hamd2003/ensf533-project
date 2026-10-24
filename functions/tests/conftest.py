import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config" / "experiment.json").read_text())

# The handlers read these at import time, exactly as on Lambda (set by CDK).
os.environ["PRIME_LIMIT"] = str(CONFIG["prime_limit"])
os.environ["DATASET_SIZE"] = str(CONFIG["dataset_size"])
os.environ["DATASET_SEED"] = str(CONFIG["dataset_seed"])
sys.path.insert(0, str(ROOT / "functions"))


class FakeContext:
    # The Python runtime exposes this as a string.
    memory_limit_in_mb = "1024"


def make_event(body=None, method="POST", base64=False):
    import base64 as b64

    raw = json.dumps(CONFIG["request_body"] if body is None else body)
    if base64:
        raw = b64.b64encode(raw.encode()).decode()
    return {
        "requestContext": {"http": {"method": method}},
        "body": raw,
        "isBase64Encoded": base64,
    }


@pytest.fixture
def config():
    return CONFIG


@pytest.fixture
def context():
    return FakeContext()
