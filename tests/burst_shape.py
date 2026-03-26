import json
import time
import os
import boto3
from locust import User, task, events, between, LoadTestShape

FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION", "json2yaml-128")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

lambda_client = boto3.client("lambda", region_name=AWS_REGION)

class LambdaUser(User):
    wait_time = between(0.1, 0.5)

    @task
    def invoke_function(self):
        start = time.perf_counter()
        func_name = FUNCTION_NAME
        try:
            response = lambda_client.invoke(
                FunctionName=func_name,
                InvocationType="RequestResponse",
                Payload=json.dumps({}),
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

class BurstShape(LoadTestShape):
    def tick(self):
        run_time = self.get_run_time()

        if run_time < 15:
            return (1, 1)
        elif run_time < 30:
            return (50, 50)
        else:
            return None
