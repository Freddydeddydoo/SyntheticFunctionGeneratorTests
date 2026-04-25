import os

from locust import User, task

from lambda_load_common import FUNCTION_NAME, invoke_lambda_report, wait_time_for_rate_profile


class LambdaUser(User):
    wait_time = wait_time_for_rate_profile()

    @task
    def invoke_function(self):
        invoke_lambda_report(FUNCTION_NAME)
