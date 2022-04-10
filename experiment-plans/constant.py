"""Constant workload
Runs an experiment with a constant workload of 1 invocation per second for 60 minutes (3600 samples).
"""

import logging
from pathlib import Path
from sb.sb import Sb


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
triggers = supported_triggers['aws'] if PROVIDER == 'aws' else supported_triggers['azure']

# Initialize sb SDK
sb = Sb(trigger_bench, log_level='DEBUG', debug=True)


# k6 workload
options = {
    "scenarios": {
        "constant": {
            "executor": "constant-arrival-rate",
            "rate": 1,
            "timeUnit": "1s",
            "duration": "60m",
            "preAllocatedVUs": 1,
            "maxVUs": 10
        }
    }
}

# Test all triggers in succession
for trigger in triggers:
    logging.info(f"Testing {trigger} trigger ...")
    sb.config.set('label', f"constant_1rps_60min_{trigger}")
    sb.config.set('trigger', trigger)
    sb.prepare()
    sb.invoke('custom', workload_options=options)
    sb.wait(5 * 60)
    sb.get_traces()
    sb.analyze_traces()

logging.info('Destroying all resources ...')
sb.cleanup()
