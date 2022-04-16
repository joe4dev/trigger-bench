import os
import logging
from dotenv import load_dotenv


BENCHMARK_CONFIG = """
trigger_bench:
  description: Measures the latency to trigger an Azure function.
  provider:
  - azure
  - pulumi
  trigger: http
  region: eastus
  runtime: node
"""
supported_triggers = ['http', 'storage', 'queue', 'database', 'serviceBus', 'eventHub', 'eventGrid', 'timer']

PULUMI_VERSION = '3.28.0'
PULUMI_IMAGE = f'pulumi/pulumi:{PULUMI_VERSION}'
PULUMI_FUNC_IMAGE = 'pulumi-azure-func'

DO_INIT = True


def prepare(spec):
    # The DB trigger requires the Azure `func` tool we install in the official Pulumi image.
    spec.build(PULUMI_FUNC_IMAGE)
    # Initialization
    if DO_INIT:
        init = ['shared', spec['trigger'], 'infra']
        init_cmd = ' && '.join([f"cd {i} && npm install && cd .." for i in init])
        spec.run(init_cmd, image='node12.x')
        if spec['trigger'] == 'database':
            db_init_cmd = 'cd database/runtimes/node && npm install && npm run build'
            spec.run(db_init_cmd, image='node12.x')
    # Deployment
    deploy_cmd = f"bash deploy.sh -t {spec['trigger']} -l {spec['region']} -r {spec['runtime']}"
    spec.run(deploy_cmd, image=PULUMI_FUNC_IMAGE)
    # Local mode:
    # run_cmd(deploy_cmd)


def invoke(spec):
    load_dotenv(override=True)
    envs = {
        'BENCHMARK_URL': os.getenv('BENCHMARK_URL')
    }
    spec.run_k6(envs)


def cleanup(spec):
    destroy_cmd = (
        'cd infra && pulumi destroy -f -y; cd ..'
        f"; cd {spec['trigger']} && pulumi destroy -f -y; cd .."
        '; cd shared && pulumi destroy -f -y; cd ..'
    )
    spec.run(destroy_cmd, image=PULUMI_IMAGE)
    # Local mode:
    # run_cmd(cmd)


def run_cmd(cmd):
    """Runs a given shell command locally.
    Requires all dependencies installed including:
    * Node.js (12)
    * Pulumi (3.28.0)
    * Azure CLI (2.34.1)
    * Azure Function Tools (4_4.0.3971)
    """
    logging.info(cmd)
    os.system(cmd)
