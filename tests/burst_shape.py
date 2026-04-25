import os

from locust import User, task, LoadTestShape

from lambda_load_common import FUNCTION_NAME, invoke_lambda_report, wait_time_for_rate_profile


class LambdaUser(User):
    wait_time = wait_time_for_rate_profile()

    @task
    def invoke_function(self):
        invoke_lambda_report(FUNCTION_NAME)


class BurstShape(LoadTestShape):

    def tick(self):
        run_time = self.get_run_time()
        if run_time < 15:
            return (1, 1)
        if run_time < 45:
            return (50, 50)
        return None
