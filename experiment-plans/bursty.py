#!/usr/bin/env python

# Usage:
# 1) Open tmux
# 2) Activate virtualenv: source sb-env/bin/activate
# 3) Run ./bursty.py 2>&1 | tee -a bursty.log

"""Bursty workload
Runs an experiment with a sequence of bursts aiming to collect 3000 samples per configuration.
"""

import logging
import sys
from pathlib import Path
from sb.sb import Sb

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# IMPORTANT: Select provider here!
PROVIDER = 'aws'  # aws or azure


# Path configuration
aws_trigger_bench = Path('../aws-triggers/trigger_benchmark.py').resolve()
azure_trigger_bench = Path('../azure-triggers/trigger_benchmark.py').resolve()
trigger_bench = aws_trigger_bench if PROVIDER == 'aws' else azure_trigger_bench

# Trigger configuration
supported_triggers = {
    'aws': ['http', 'storage', 'queue'],
    'azure': ['http', 'storage', 'queue', 'database', 'serviceBus', 'eventHub', 'eventGrid', 'timer'],
}
logging.info(f"Using provider {PROVIDER}.")
triggers = supported_triggers['aws'] if PROVIDER == 'aws' else supported_triggers['azure']

# Burst sizes
burst_sizes = [10, 50, 100, 300]
inter_burst_time_seconds = 10
num_target_samples = 3000


def k6_options(burst_size):
    """Returns a k6 workload config for a given burst size.
    * k6 advanced scenarios with startTime: https://k6.io/docs/using-k6/scenarios/advanced-examples/
    * k6 iteration executor: https://k6.io/docs/using-k6/scenarios/executors/per-vu-iterations/
    """
    num_bursts = round(num_target_samples / burst_size)
    options = {
        "scenarios":{
            f"burst_{burst+1}": {
                "executor": "per-vu-iterations",
                "vus": burst_size,
                "iterations": 1,
                "startTime": f"{inter_burst_time_seconds*burst}s",
            } for burst in range(num_bursts)
        }
    }
    return options


# Initialize sb SDK
sb = Sb(trigger_bench, log_level='DEBUG', debug=True)

# Test all triggers in succession
MINUTE = 60
for trigger in triggers:
    logging.info(f"Testing {trigger} trigger ...")
    sb.config.set('label', f"bursty_3000_invocations_{trigger}")
    sb.config.set('trigger', trigger)
    sb.prepare()
    # Test different burst sizes
    for burst_size in burst_sizes:
        sb.config.set('burst_size', burst_size)
        sb.wait(1 * MINUTE)
        options = k6_options(burst_size)
        sb.invoke('custom', workload_options=options)
        # Wait until traces are recorded and processed by the tracing infrastructure.
        # * AWS X-Ray tends to be ready within 1-2 minutes for small bursts
        # * Azure Insights can take over 5-10 minutes until the traces appear
        sb.wait(10 * MINUTE)
        sb.get_traces()
        # Save bandwidth by analyzing after downloading from the cloud host
        # sb.analyze_traces()

logging.info('Destroying all resources ...')
sb.cleanup()
