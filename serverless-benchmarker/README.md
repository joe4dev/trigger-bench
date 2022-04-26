# Serverless Benchmarker

The Serverless Benchmarker (sb) is a meta-benchmarking tool to orchestrate reproducible serverless application benchmarking.

* **Reproducible deployments**: sb abstracts away dependencies using Docker and automatically mounts application code and credentials (when needed) into the right container directories.
* **Automated load generation**: sb provides different classes of invocation patterns derived from real-world traces. It integrates with the open source load testing tool [k6](https://k6.io/).
* **Clear box application insights**: for instrumented applications, sb implements detailed trace analysis using distributed tracing such as [AWS X-Ray](https://aws.amazon.com/xray/) and [Azure Application Insights](https://docs.microsoft.com/en-us/azure/azure-monitor/app/distributed-tracing).

## Quicklinks

* [Development](./docs/DEVELOPMENT.md)
* [FAQ](./docs/FAQ.md)

## Quick Setup

1. Install [Docker](https://docs.docker.com/get-docker/) 19.03+
2. Install [Python](https://www.python.org/downloads/) 3.7+ and [pipx](https://packaging.python.org/guides/installing-stand-alone-command-line-tools/)

    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath  # ensures the path of the CLI application directory is on your $PATH
    ```

3. Install the `sb` CLI tool
    1. `cd serverless-benchmarker`
    2. `pipx install --editable .`  
    a) You may need to restart your terminal for the path updates to take effect.  
    b) During development, editable allows to just pull the latest changes without re-installing.  
    c) Alternatively use [venv](https://docs.python.org/3/library/venv.html) to create `python3 -m sb-env` and activate `source sb-env/bin/activate` (depends on shell) a virtual environment.
4. Build the sb Dockerfile via `sb init`
5. Login for providers via `sb login PROVIDER`: Supported for [aws](./docs/AWS.md), [azure](./docs/AZURE.md), `google`, `ibm`.

NOTE: The credentials are stored in a Docker volume called `PROVIDER-secrets` (e.g., `aws-secrets`) and selectively mounted when needed. They can be deleted via `sb logout PROVIDER`.

## Getting Started

```sh
# Run empty mock benchmark locally
sb test --file=tests/fixtures/mock_benchmark/mock_benchmark.py

# AWS
cd thumbnail-generator/AWS
# Azure
cd thumbnail-generator/Azure

# Benchmarking lifecycle using a `*_benchmark.py` file:
# 1) Deploy app
sb prepare
# 2a) Invoke app a single time
sb invoke
# 2b) Invoke app 10 times sequentially
sb invoke 10
# 2c) Benchmark with a pre-configured workload_type (constant|bursty|spikes|jump)
sb invoke bursty
# 3) Download traces
sb get_traces
# 4) Analyze latest traces
sb analyze_traces
# Hint for analyzing previous traces: sb analyze_traces logs/DATETIME/traces.json
# 5) Cleanup all cloud infrastructure
sb cleanup
```

*Hints:*

* `*_benchmark.py` files in the current working directory are automatically detected (if only a single file exists).
* `sb test` sequentially executes prepare, invoke (with workload_type=3) and, cleanup.
* `sb invoke custom_per_minute_rate_trace.csv` supports custom CSV workload traces.
* Checkout the [AWS X-Ray Console](https://console.aws.amazon.com/xray/home) for result traces (6h retention!) or [CloudWatch logs](https://console.aws.amazon.com/cloudwatch).

## Debugging

* `sb shell IMAGE` starts an interactive shell with all auto-mounts in a given Docker IMAGE.
* More examples of `*_benchmark.py` files are available under `tests/fixtures` (covered by integration tests)
* Insert the code `import code; code.interact(local=dict(globals(), **locals()))` on any line to prompt an interactive Python shell.
* Checkout the [DEVELOPMENT](docs/DEVELOPMENT.md) docs for more details.

## Add your Application

1. Create a `*_benchmark.py` file in the main directory of your application.
2. Implement hooks for `prepare(spec)`, `invoke(spec)`, and `cleanup(spec)` as shown under [mock_benchmark.py](./tests/fixtures/mock_benchmark/mock_benchmark.py). Key functionality:
    * `spec.run(CMD, image=DOCKERIMAGE)` Runs a given CMD in a DOCKERIMAGE and returns its stdout.
    * `spec.build(IMAGE_TAG)` Builds a Dockerfile and tags it with IMAGE_TAG.
    * `spec['KEY']` provides a persistent key-value store across different benchmark cycles (e.g., share state between prepare and invoke)
    * The `BENCHMARK_CONFIG` constant initializes the key-value store and specifies configurable attributes (e.g., region) and meta-information (e.g., provider).
    * The working directory is defined by the location of `*_benchmark.py` (i.e., same directory).
    * sb mounts the working directory by default into any Docker container. If files at higher levels are required, the `root` benchmark config allows to mount higher level directories (e.g., parent using `..`).
    * sb integrates with [k6](https://k6.io/) for load testing.
    * `sb invoke` automatically generates a `workload_options.json` file with [k6 options](https://k6.io/docs/using-k6/options).
    * `sb invoke` and `sb get_traces` automatically create logs in the working directory under `logs` with the start timestamp of the invocation.
3. Instrument your application (provider- and language-dependent):
    * AWS: Enable X-Ray tracing and add language-specific instrumentation as described [here](https://docs.aws.amazon.com/lambda/latest/dg/services-xray.html).
    * Azure: Use [Azure Insights](https://docs.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview) metrics for [distributed tracing](https://docs.microsoft.com/en-us/azure/azure-monitor/app/distributed-tracing)
