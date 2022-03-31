BENCHMARK_CONFIG = """
trigger_bench:
  description: Measures the latency to trigger an AWS Lambda function.
  provider:
  - aws
  - pulumi
  trigger: queue
  region: us-east-1
"""
supported_triggers = ['http', 'queue', 'storage']
PULUMI_IMAGE = 'pulumi/pulumi:3.27.0'

# Pulumi example: https://github.com/perfkit/pulumi-examples/blob/master/aws-ts-apigateway/count_api_benchmark.py


def prepare(spec):
    trigger = spec['trigger']
    # Initialization
    init = ['shared', trigger, 'infra']
    init_cmd = ' && '.join([f"cd {i} && npm install && cd .." for i in init])
    spec.run(init_cmd, image='node12.x')
    # Deploy shared resources
    shared_cmd = (
        'cd shared'
        ' && pulumi stack select shared -c'
        f" && pulumi config set aws:region {spec['region']}"
        ' && pulumi up -f -y'
    )
    spec.run(shared_cmd, image=PULUMI_IMAGE)
    # Deploy receiving function 2 with trigger
    receiver_cmd = (
        f"cd {trigger}"
        f" && pulumi stack select {trigger} -c"
        f" && pulumi config set aws:region {spec['region']}"
        ' && pulumi up -f -y'
    )
    spec.run(receiver_cmd, image=PULUMI_IMAGE)
    spec['receiver'] = last_line(spec.run(f"cd {trigger} && pulumi stack output url", image=PULUMI_IMAGE))
    # Deploy invoking function 1 called infra
    infra_cmd = (
        'cd infra'
        ' && pulumi stack select infra -c'
        f" && pulumi config set aws:region {spec['region']}"
        ' && pulumi up -f -y'
    )
    spec.run(infra_cmd, image=PULUMI_IMAGE)
    spec['invoker'] = last_line(spec.run('cd infra && pulumi stack output url', image=PULUMI_IMAGE))
    spec['benchmark_url'] = f"{spec['invoker']}?trigger={trigger}&input={spec['receiver']}"


def invoke(spec):
    envs = {
        'BENCHMARK_URL': spec['benchmark_url']
    }
    spec.run_k6(envs)


def cleanup(spec):
    # shared needs to be destroyed last as it is a dependency
    stacks = ['infra', *supported_triggers, 'shared']
    for stack in stacks:
        pulumi_destroy(spec, stack)


def pulumi_destroy(spec, stack):
    """Destroys a Pulumi stack."""
    cmd = (
        f"cd {stack}"
        ' && pulumi destroy -f -y'
    )
    spec.run(cmd, image=PULUMI_IMAGE)


def last_line(log) -> str:
    """Returns the last line of a multiline string.
    This is a workaround to ignore any leading error messages
    potentially printed to sterr or stdout.
    For example: Pulumi new version available. Docker platform warning."""
    return log.splitlines()[-1].rstrip()
