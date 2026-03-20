import boto3
import json
from locust import User, task, between, events
import time

lambda_client = boto3.client("lambda", region_name="us-east-1")

class LambdaUser(User):
    wait_time = between(1, 2)

    @task
    def invoke_lambda(self):
        start_time = time.time()
        try:
            response = lambda_client.invoke(
                FunctionName="floatoperations-512",
                InvocationType="RequestResponse",
                Payload=json.dumps({})
            )
            duration = (time.time() - start_time) * 1000
            response_payload = json.loads(response["Payload"].read())
            if response.get("FunctionError"):
                events.request.fire(
                    request_type="Lambda",
                    name="floatoperations-512",
                    response_time=duration,
                    response_length=0,
                    exception=response_payload
                )
            else:
                events.request.fire(
                    request_type="Lambda",
                    name="floatoperations-512",
                    response_time=duration,
                    response_length=0,
                    exception=None
                )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="Lambda",
                name="floatoperations-512",
                response_time=duration,
                response_length=0,
                exception=e
            )