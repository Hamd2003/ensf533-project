"""In-memory data processing workload: sort, filter and aggregate records.

The dataset is generated once per execution environment at import time, so
generation cost only shows up in init duration (cold starts), not per request.
"""

import os
import random

import common

WORKLOAD = "data"
DATASET_SIZE = int(os.environ["DATASET_SIZE"])
DATASET_SEED = int(os.environ["DATASET_SEED"])

CATEGORIES = [f"c{i}" for i in range(10)]
VALUE_THRESHOLD = 500.0  # values are uniform in [0, 1000), so ~half pass the filter
CHECKSUM_MOD = 1_000_000_007  # keeps the checksum below 2**53 so JS clients parse it exactly
TS_BASE = 1_700_000_000


def generate_dataset(size, seed):
    rng = random.Random(seed)
    return [
        {
            "id": i,
            "category": CATEGORIES[rng.randrange(len(CATEGORIES))],
            "value": rng.random() * 1000.0,
            "ts": TS_BASE + rng.randrange(31_536_000),
        }
        for i in range(size)
    ]


DATASET = generate_dataset(DATASET_SIZE, DATASET_SEED)


def summarize(records):
    # sorted() returns a new list; DATASET keeps its original unsorted order, so
    # every request pays for a full sort (Timsort on sorted input is far faster).
    ordered = sorted(records, key=lambda r: r["value"])
    selected = [r for r in ordered if r["value"] >= VALUE_THRESHOLD]

    counts = {c: 0 for c in CATEGORIES}
    total = 0.0
    checksum = 0
    for position, r in enumerate(selected, start=1):
        counts[r["category"]] += 1
        total += r["value"]
        # Position-weighted, so the checksum also verifies the sort order.
        checksum = (checksum + position * r["id"]) % CHECKSUM_MOD

    n = len(selected)
    return {
        "input_records": len(records),
        "selected_records": n,
        "min_value": round(selected[0]["value"], 6) if n else None,
        "max_value": round(selected[-1]["value"], 6) if n else None,
        "mean_value": round(total / n, 6) if n else None,
        "category_counts": counts,
        "checksum": checksum,
    }


def compute(_payload):
    return summarize(DATASET)


def handler(event, context):
    return common.handle(event, context, WORKLOAD, compute)
