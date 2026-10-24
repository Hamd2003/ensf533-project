"""CPU-bound workload: count primes
"""

import math
import os

import common

WORKLOAD = "cpu"
PRIME_LIMIT = int(os.environ["PRIME_LIMIT"])


def count_primes(limit):
    if limit < 2:
        return 0
    count = 1  # the prime 2; only odd candidates and odd divisors below
    for n in range(3, limit + 1, 2):
        for d in range(3, math.isqrt(n) + 1, 2):
            if n % d == 0:
                break
        else:
            count += 1
    return count


def compute(_payload):
    return {"prime_count": count_primes(PRIME_LIMIT)}


def handler(event, context):
    return common.handle(event, context, WORKLOAD, compute)
