#!/usr/bin/env python

"""Script to analyze new traces.json files.
Requires a Python environment with sb installed.
"""

from pathlib import Path
import os
import logging
import sys
import yaml
from sb.sb import Sb
from data_importer import parse_provider


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


# Trigger-bench directory
root_dir = Path(__file__).parent.parent.resolve()
default_data_path = root_dir / 'data'
data_path = os.environ.get('SB_DATA_DIR') or default_data_path

# Force reanalysis (e.g., after updates to analyzer)
always_analyze = False

print(f"Analyze new traces.json files in {data_path}")
traces = list(data_path.glob('**/traces.json'))
sb = Sb()
for trace in traces:
    log_dir = trace.parent
    trigger = log_dir / 'trigger.csv'
    if always_analyze or not trigger.is_file():
        config_file = log_dir / 'sb_config.yml'
        with open(config_file) as file:
            sb_config = yaml.safe_load(file)
            provider = parse_provider(sb_config['trigger_bench'])
            logging.debug(f"{provider},{trace}")
            sb.analyze_traces(trace, provider)
