"""Lightweight API workload: validate a small fixed schema and echo it back."""

import common

WORKLOAD = "api"


def validate(payload):
    if not isinstance(payload, dict):
        raise common.BadRequest("body must be a JSON object")

    user_id = payload.get("user_id")
    item = payload.get("item")
    quantity = payload.get("quantity")

    if not isinstance(user_id, str) or not user_id:
        raise common.BadRequest("user_id must be a non-empty string")
    if not isinstance(item, str):
        raise common.BadRequest("item must be a string")
    # bool is a subclass of int in Python; reject true/false explicitly.
    if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 100:
        raise common.BadRequest("quantity must be an integer between 1 and 100")

    return {"user_id": user_id, "item": item, "quantity": quantity}


def handler(event, context):
    return common.handle(event, context, WORKLOAD, validate)
