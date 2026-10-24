import json

import pytest

import api
import common
import cpu
import data
from conftest import make_event

HANDLERS = [api, cpu, data]
CONTRACT_FIELDS = {"ok", "workload", "memory_mb", "result", "compute_ms", "env_id", "cold"}


def call(module, event, context):
    response = module.handler(event, context)
    assert response["headers"] == {"content-type": "application/json"}
    return response["statusCode"], json.loads(response["body"])


@pytest.mark.parametrize("module", HANDLERS, ids=lambda m: m.WORKLOAD)
def test_valid_request_returns_expected_result(module, context, config):
    status, body = call(module, make_event(), context)
    assert status == 200
    assert set(body) == CONTRACT_FIELDS
    assert body["ok"] is True
    assert body["workload"] == module.WORKLOAD
    assert body["memory_mb"] == 1024
    assert body["result"] == config["expected_results"][module.WORKLOAD], (
        "expected_results is stale; run python3 tools/update_expected.py"
    )
    assert body["env_id"] == common.ENV_ID
    assert body["compute_ms"] >= 0


@pytest.mark.parametrize("module", HANDLERS, ids=lambda m: m.WORKLOAD)
def test_output_is_deterministic(module, context):
    _, first = call(module, make_event(), context)
    _, second = call(module, make_event(), context)
    assert first["result"] == second["result"]
    assert first["env_id"] == second["env_id"]


@pytest.mark.parametrize("module", HANDLERS, ids=lambda m: m.WORKLOAD)
@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE", "HEAD"])
def test_non_post_is_rejected(module, method, context):
    status, body = call(module, make_event(method=method), context)
    assert status == 405
    assert body["ok"] is False


@pytest.mark.parametrize("module", HANDLERS, ids=lambda m: m.WORKLOAD)
def test_base64_body_is_accepted(module, context, config):
    status, body = call(module, make_event(base64=True), context)
    assert status == 200
    assert body["result"] == config["expected_results"][module.WORKLOAD]


def test_cold_flag_only_on_first_invocation(context, monkeypatch):
    monkeypatch.setattr(common, "_invocations", 0)
    _, first = call(api, make_event(), context)
    _, second = call(api, make_event(), context)
    assert first["cold"] is True
    assert second["cold"] is False


@pytest.mark.parametrize("body", [
    {},
    {"user_id": "", "item": "widget", "quantity": 3},
    {"user_id": 7, "item": "widget", "quantity": 3},
    {"user_id": "u-1", "item": None, "quantity": 3},
    {"user_id": "u-1", "item": "widget", "quantity": 0},
    {"user_id": "u-1", "item": "widget", "quantity": 101},
    {"user_id": "u-1", "item": "widget", "quantity": "3"},
    {"user_id": "u-1", "item": "widget", "quantity": 3.0},
    {"user_id": "u-1", "item": "widget", "quantity": True},
    ["not", "an", "object"],
])
def test_api_rejects_malformed_body(body, context):
    status, response = call(api, make_event(body=body), context)
    assert status == 400
    assert response["ok"] is False


def test_api_rejects_invalid_json(context):
    event = make_event()
    event["body"] = "{not json"
    status, _ = call(api, event, context)
    assert status == 400


def test_count_primes_small_values():
    assert [cpu.count_primes(n) for n in (0, 1, 2, 3, 10, 100, 1000)] == [0, 0, 1, 2, 4, 25, 168]


def test_data_request_does_not_sort_dataset_in_place(context):
    before = [r["id"] for r in data.DATASET[:100]]
    call(data, make_event(), context)
    assert [r["id"] for r in data.DATASET[:100]] == before
    # The original order must stay unsorted, otherwise later requests get cheaper.
    values = [r["value"] for r in data.DATASET]
    assert values != sorted(values)
