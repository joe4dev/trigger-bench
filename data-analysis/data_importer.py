from tkinter import OFF
from typing import List
import pandas as pd
from datetime import datetime, timedelta
import pathlib
import yaml
import logging
import os
# NOTE: Requires Python 3.10: https://docs.python.org/3/library/itertools.html#itertools.pairwise
from itertools import pairwise

# Configure paths
script_dir = pathlib.Path(__file__).parent.resolve()

## Input data directory
default_data_path = script_dir.parent / 'data'
data_path = default_data_path
if os.environ.get('DATA_PATH'):
    data_path = pathlib.Path(os.environ['DATA_PATH'])

## Output directory for plots
default_plots_path = script_dir / 'plots'
plots_path = default_plots_path
if os.environ.get('PLOTS_PATH'):
    plots_path = pathlib.Path(os.environ['PLOTS_PATH'])
else:
    plots_path.mkdir(exist_ok=True)

# Constants
TRIGGER_CSV = 'trigger.csv'
NUM_EXTRA_TIMESTAMPS = 5
OFFSET = 5

EXTRA_TIMESTAMPS = [f"t{n}" for n in range(OFFSET, NUM_EXTRA_TIMESTAMPS+OFFSET)]
DATE_COLS = [
    't1',
    't2',
    't3',
    't4',
    *EXTRA_TIMESTAMPS
]
TIMEDELTA_COLS = [
    'trigger_time',
    'service_time',
    'init_overhead',
    *[f"{col1}{col2}" for col1, col2 in pairwise(EXTRA_TIMESTAMPS)],
]

TRIGGER_MAPPINGS = {
    'http': 'HTTP',
    'queue': 'Queue',
    'storage': 'Storage',
    'database': 'Database',
    'serviceBus': 'Service Bus',
    'eventHub': 'Event Hub',
    'eventGrid': 'Event Grid',
    'timer': 'Timer'
}

LABEL_MAPPINGS = {
    'constant_http': 'HTTP',
    'constant_storage': 'Storage',
    'constant_queue': 'Queue',
}

PROVIDER_MAPPINGS = {
    'aws': 'AWS',
    'azure': 'Azure',
}

DURATION_MAPPINGS = {
    'trigger_time': 'Trigger',
    'service_time': 'Service',
    'init_overhead': 'Initialization',
}

# Import helper methods

def find_execution_paths(data_path) -> List[pathlib.Path]:
    "Returns a list of paths to log directories where 'trigger.csv' exists."
    # Execution log directories are in the datetime format 2021-04-30_01-09-33
    return [p.parent for p in pathlib.Path(data_path).rglob(TRIGGER_CSV)]


def read_sb_app_config(execution):
    """Returns a dictionary with the parsed sb config from sb_config.yml"""
    config_path = execution / 'sb_config.yml'
    sb_config = {}
    app_config = {}
    app_name = ''
    if config_path.is_file():
        with open(config_path) as f:
            sb_config = yaml.load(f, Loader=yaml.FullLoader)
        app_name = list(sb_config.keys())[0]
        # Workaround for cases where sb is the first key
        if app_name == 'sb':
            app_name = list(sb_config.keys())[1]
        app_config = sb_config[app_name]
    else:
        logging.warning(f"Config file missing at {config_path}.")
        return dict()
    return app_config, app_name


def parse_provider(app_config) -> str | None:
    """Returns a single provider string parsing an sb config for a specific app/benchmark,
    which could contain a list of multiple providers (e.g., aws + pulumi)."""
    provider = app_config.get('provider')
    if provider and 'aws' in provider:
        return 'aws'
    elif provider and 'azure' in provider:
        return 'azure'
    else:
        logging.error('Unsupported provider for trace analyzer')
        return None


def read_trigger_csv(execution) -> pd.DataFrame:
    """Returns a pandas dataframe with the parsed trigger.csv"""
    trigger_path = pathlib.Path(execution) / TRIGGER_CSV
    if not trigger_path.is_file:
        raise Exception(f"Missing trigger file at {trigger_path}")
    return pd.read_csv(trigger_path, parse_dates=DATE_COLS)


def filter_traces_warm(df) -> pd.DataFrame:
    return df[(df["coldstart_f1"] == False) & (df["coldstart_f2"] == False)]


def calculate_durations(trigger):
    "Adds timedelta columns with durations."
    # Fix SettingWithCopyWarning
    df = trigger.copy()
    # Calculate selected durations
    df['trigger_time'] = df['t4'] - df['t1']
    df['service_time'] = df['t2'] - df['t1']
    df['init_overhead'] = df['t4'] - df['t3']
    # Calculate timestamp overhead
    for col1, col2 in pairwise(EXTRA_TIMESTAMPS):
        df[f"{col1}{col2}"] = df[col2] - df[col1]
    return df
