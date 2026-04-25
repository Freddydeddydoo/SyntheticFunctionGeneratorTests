import json
import os
import time

import boto3
from botocore.config import Config
from locust import events

FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION", "decompress-128")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

_client = None

_BOTO_CONFIG = Config(
    retries={"max_attempts": 2, "mode": "standard"},
    read_timeout=30,
    connect_timeout=10,
)


def lambda_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "lambda",
            region_name=AWS_REGION,
            config=_BOTO_CONFIG,
        )
    return _client


def _invoke_payload_bytes() -> bytes:
    raw = os.environ.get("LOCUST_LAMBDA_PAYLOAD")
    if raw:
        return raw.encode("utf-8") if isinstance(raw, str) else raw
    return json.dumps({"warmup": True}).encode("utf-8")


def invoke_lambda_report(func_name: str) -> None:
    start = time.perf_counter()
    try:
        response = lambda_client().invoke(
            FunctionName=func_name,
            InvocationType="RequestResponse",
            Payload=_invoke_payload_bytes(),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        payload = json.loads(response["Payload"].read())

        if "FunctionError" in response:
            error_msg = payload.get("errorMessage", "unknown lambda error")
            events.request.fire(
                request_type="lambda",
                name=func_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=Exception(error_msg),
            )
        else:
            events.request.fire(
                request_type="lambda",
                name=func_name,
                response_time=elapsed_ms,
                response_length=len(json.dumps(payload)),
            )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        events.request.fire(
            request_type="lambda",
            name=func_name,
            response_time=elapsed_ms,
            response_length=0,
            exception=e,
        )


def wait_time_for_rate_profile():
    from locust import between

    profile = os.environ.get("LOCUST_RATE_PROFILE", "med").strip().lower()
    profiles = {
        "low": (1.5, 3.0),
        "med": (0.2, 0.8),
        "high": (0.02, 0.12),
    }
    lo, hi = profiles.get(profile, profiles["med"])
    return between(lo, hi)
