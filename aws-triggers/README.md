# AWS TriggerBench

## Requirements

* [Serverless Benchmarker (SB)](../serverless-benchmarker/README.md) for benchmark orchestration and trace analysis.
* [Pulumi account](https://www.pulumi.com/docs/intro/pulumi-service/accounts/) for Infrastructure-as-Code deployment automation.
* [AWS account](../serverless-benchmarker/docs/AWS.md) for cloud resource provisioning.

## Setup

1. Install [sb](../serverless-benchmarker/README.md)
2. `sb login pulumi`
3. `sb login aws`

## Execution

1. Select trigger type in [trigger_benchmark.py](./trigger_benchmark.py)
2. `sb prepare` to deploy the selected trigger, its invoker function (infra), and shared resources (shared).
3. `sb invoke 100` to invoke the trigger 100 times.
4. `sb wait 120 get_traces analyze_traces` to wait 120s (2min), download traces, and analyze them. Waiting time is required as it might take several minutes until the traces appear in AWS X-Ray.
5. `sb cleanup` to destroy all resources.
