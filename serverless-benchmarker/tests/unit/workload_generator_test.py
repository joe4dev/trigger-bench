import json
import os
from sb.workload_generator import WorkloadGenerator


def test_default_workload():
    actual = json_options('single')
    assert actual == '{"vus": 1, "iterations": 1}'


def test_invoke_numeric_workload():
    actual = json_options(10)
    assert actual == '{"vus": 1, "iterations": 10}'


def test_jump_workload():
    """Tests generating a second-based workload from a minute-based invocation rate trace.
    Do not ignore any seconds at the start (enabled by default to fix bootstrapping issue).
    """
    seconds_to_skip = 0
    actual = json_options('jump', 1, 'linear', None, None, seconds_to_skip)
    expected_start = '''{"scenarios": {"benchmark_scenario": {"executor": "ramping-arrival-rate", "startRate": 0, "timeUnit": "1s", "preAllocatedVUs": 1, "stages": [{"target": 0, "duration": "13s"}, {"target": 1, "duration": "1s"}, {"target": 1, "duration": "1s"}, {"target": 0, "duration": "1s"}, {"target": 1, "duration": "1s"}, {"target": 1, "duration": "21s"}'''  # noqa: E501
    assert actual.startswith(expected_start)


def test_steady_workload():
    actual = json_options('spikes')
    expected_start = '''{"scenarios": {"benchmark_scenario": {"executor": "ramping-arrival-rate", "startRate": 0, "timeUnit": "1s", "preAllocatedVUs": 1, "stages": [{"target": 0, "duration": "180s"}, {"target": 5, "duration": "1s"}, {"target": 5, "duration": "19s"}'''  # noqa: E501
    assert actual.startswith(expected_start)


# Helper returning a JSON-string based on given args for the workload generator
def json_options(*args):
    # Ensure fixed seed
    os.environ['SB_WORKLOADGEN_SEED'] = '11'
    generator = WorkloadGenerator(*args)
    workload_dict = generator.generate_trace()
    return json.dumps(workload_dict)
