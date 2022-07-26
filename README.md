# Serverless TriggerBench

This repository contains the aws ([aws-triggers](./aws-triggers/), [azure-triggers](./azure-triggers/)) and [data analysis](./data-analysis/) scripts of the TriggerBench cross-provider serverless benchmark.
It also bundles a customized extension of the [serverless benchmarker](./serverless-benchmarker/) tool to automate and analyze serverless performance experiments.

The dataset (i.e., `data` directory) is only included in the Zenodo replication package due to its size (>1GB).
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6783287.svg)](https://doi.org/10.5281/zenodo.6783287)

## TriggerBench

TriggerBench currently supports three triggers on AWS and eight triggers on Microsoft Azure.

| Trigger  | AWS Service                                                                                             | Azure Service                                                                                 |
|----------|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| HTTP     | [API Gateway](https://aws.amazon.com/api-gateway/)                                                      | [API Management](https://azure.microsoft.com/en-us/services/api-management)                   |
| Queue    | [SQS](https://aws.amazon.com/sqs/)                                                                      | [Queue Storage](https://azure.microsoft.com/en-us/services/storage/queues/)                   |
| Storage  | [S3](https://aws.amazon.com/s3/)                                                                        | [Blob Storage](https://azure.microsoft.com/en-us/services/storage/blobs/)                     |
| Database | [DynomoDB](https://aws.amazon.com/dynamodb/)¹                                                           | [CosmosDB](https://azure.microsoft.com/en-us/services/cosmos-db/)                             |
| Event    | [SNS](https://aws.amazon.com/sns)¹                                                                      | [Event Grid](https://azure.microsoft.com/en-us/services/event-grid)                           |
| Stream   | [Kinesis](https://aws.amazon.com/kinesis/)¹                                                             | [Event Hubs](https://azure.microsoft.com/en-us/services/event-hubs/)                          |
| Message  | [EventBridge](https://aws.amazon.com/eventbridge/)¹                                                     | [Service Bus Topic](https://azure.microsoft.com/en-us/services/service-bus)                   |
| Timer    | [CloudWatch Events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html)¹ | [Timer](https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer)      |

¹ Not implemented.

## Dataset

> The `data` directory is only included in the Zenodo replication package due to its size (>1GB).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6783287.svg)](https://doi.org/10.5281/zenodo.6783287)

The `aws` and `azure` sub-directories contain data from benchmark executions from April 2022.
Each execution is a separate directory with a timestamp in the format `yyyy-mm-dd-HH-MM-SS` (e.g., `2022-04-15_21-58-52`) and contains the following files:

* `k6_metrics.csv`: Load generator HTTP client logs in CSV format (see [K6 docs](https://k6.io/docs/results-visualization/csv/))
* `sb_config.yml`: serverless benchmarker execution configuration including experiment label.
* `trigger.csv`: analyzer output CSV per trace.
  * `root_trace_id`: The trace id created by k6 and adopted by the invoker function
  * `child_trace_id`: The trace id newly created by the receiver function if trace propagation is not supported (this is the case for most asynchronous triggers)
  * `t1`-`t4`: Timestamps following the trace model (see paper)
  * `t5`-`t9`: Additional timestamps for measuring timestamping overhead
  * `coldstart_f1=True|False`: coldstart status for invoker (f1) and receiver (f2) functions
* `trace_ids.txt`: text file with each pair of `root_trace_id` and `child_trace_id` on a new line.
* `traces.json`: raw trace JSON representation as retrieved from the provider tracing service. For AWS, see [X-Ray segment docs](https://docs.aws.amazon.com/xray/latest/devguide/xray-api-segmentdocuments.html). For Azure, see [Application Insights telemetry data model](https://docs.microsoft.com/en-us/azure/azure-monitor/app/data-model).
* `workload_options.json`: [K6 load scenario](https://k6.io/docs/using-k6/scenarios/) configuration.

## Replicate Data Analysis

### Installation

1. Install [Python](https://www.python.org/downloads/) 3.10+
2. Install Python dependencies `pip install -r requirements.txt`

### Create Plots

1. Run `python plots.py` generates the plots and the statistical summaries presented in the paper.

By default, the plots will be saved into a `plots` sub-directory.
An alternative output directory can be configured through the environment variable `PLOTS_PATH`.

> Hint: For interactive development, we recommend the VSCode [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) in [interactive mode](https://youtu.be/lwN4-W1WR84?t=107).

## Replicate Cloud Experiments

The following experiment plan automate benchmarking experiments with different types workloads (constant and bursty).
This generates a new dataset in the same format as described above.

1. Set up a load generator as vantage point following the description in [LOADGENERATOR](./serverless-benchmarker/docs/LOADGENERATOR.md).
2. Choose the `PROVIDER` (aws or azure) in the [constant.py](./experiment-plans/constant.py) experiment plan
3. Run the [constant.py](./experiment-plans/constant.py) experiment plan
    1. Open tmux
    2. Activate virtualenv `source sb-env/bin/activate`
    3. Run `./constant.py 2>&1 | tee -a constant.log`

## Contributors

The initial trigger implementations for AWS and Azure are based on two master thesis projects at Chalmers University of Technology in Sweden supervised by Joel:

* AWS + Azure: **[Performance Comparison of Function-as- a-Service Triggers: A Cross-Platform Performance Study of Function Triggers in Function-as-a-Service](https://odr.chalmers.se/handle/20.500.12380/302822)** by Marcus Bertilsson and Oskar Grönqvist, 2021.
* Azure Extension: **[Serverless Function Triggers in Azure: An Analysis of Latency and Reliability](https://odr.chalmers.se/handle/20.500.12380/305138)** by Henrik Lagergren and Henrik Tao, 2022.

Joel contributed many improvements to their original source code as documented in the import commits [a00b67a](https://github.com/joe4dev/trigger-bench/commit/a00b67a1dd8476ca77d026e59adf2674c7807e68) and [6d2f5ef](https://github.com/joe4dev/trigger-bench/commit/6d2f5ef8bda0596b3f295cb6c6cbeba212c6ef43) and developed TriggerBench as integrated benchmark suite (see commit history for detailed changelog).
