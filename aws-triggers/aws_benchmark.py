import logging
import re

BENCHMARK_CONFIG = """
aws_benchmark:
  description: AWS trigger benchmark.
  provider:
  - aws
  - pulumi
  region: eu-central-1
"""

# WORKING EXAMPLE: https://github.com/perfkit/pulumi-examples/blob/master/aws-ts-apigateway/count_api_benchmark.py
def prepare(spec):
    logging.info('prepare(): building and deploying AWS trigger benchmark')
    trigger_type = 'http'
    log = spec.run('./deploy.sh -t ' + trigger_type + ' | grep http | tail -1', image='pulumi/pulumi:v2.25.2').rstrip()
    urls = re.findall("^.*execute-api.*$", log, re.MULTILINE)
    spec['endpoint'] = urls[0]


def invoke(spec):
    logging.info('invoke(): invoke app a single time')
    envs = {
        'URL': spec['endpoint']
    }
    spec.run_k6(envs)


def cleanup(spec):
    logging.info('cleanup(): delete all functions and resources')
    spec.run('./destroy.sh', image='pulumi/pulumi:v2.25.2')
