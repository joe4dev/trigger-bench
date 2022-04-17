"""
Generates all plots by loading and analyzing all executions
"""

# %% Imports
import sys
from data_importer import *
from plotnine import *

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# %% Load data
execution_paths = find_execution_paths(data_path)
trigger_dfs = []
for execution in execution_paths:
    app_config, app_name = read_sb_app_config(execution)
    trigger = read_trigger_csv(execution)
    trigger['provider'] = parse_provider(app_config)
    trigger['label'] = app_config.get('label', None)
    trigger['trigger'] = app_config.get('trigger', None)
    trigger_dfs.append(trigger)

# Combine data frames
traces = pd.concat(trigger_dfs)

# %% Preprocess data
warm_traces = filter_traces_warm(traces)
durations = calculate_durations(warm_traces)
durations_long = pd.melt(durations, id_vars=['root_trace_id', 'child_trace_id', 'provider', 'trigger', 'label'], var_name='duration_type', value_vars=TIMEDELTA_COLS, value_name='duration')
durations_long['duration_ms'] = durations_long['duration'].dt.total_seconds() * 1000

# Rename and reorder categories
# TODO: remap triggers
# durations_long['workload_type'] = durations_long['label'].map(label_mappings)
# durations_long['workload_type'] = pd.Categorical(durations_long['workload_type'],
#                                                  categories=label_mappings.values(),
#                                                  ordered=True)
durations_long['provider'] = durations_long['provider'].map(PROVIDER_MAPPINGS)
durations_long['provider'] = pd.Categorical(durations_long['provider'],
                                            categories=PROVIDER_MAPPINGS.values(),
                                            ordered=True)
durations_long['duration_type'] = durations_long['duration_type'].map(DURATION_MAPPINGS)
durations_long['duration_type'] = pd.Categorical(durations_long['duration_type'],
                                            categories=DURATION_MAPPINGS.values(),
                                            ordered=True)

# Remove negative timediffs
# TODO: Print warning if this happens
durations_long = durations_long.drop(durations_long[durations_long['duration_ms']<0].index)

# Clip data because catplot doesn't support dynamic limits
# and the tail is too long to be shown.
# Important: Disclose if using this.
# Based on StackOverflow: https://stackoverflow.com/a/54356494
def is_outlier(s):
    lower_limit = s.min()
    # upper_limit = s.quantile(.95)
    upper_limit = s.median() + 3 * s.std()
    return ~s.between(lower_limit, upper_limit)

# durations_long_filtered = durations_long.loc[~durations_long.groupby(['provider', 'workload_type', 'duration_type'])['duration_ms'].apply(is_outlier), :].reset_index(drop=True)
durations_long_filtered = durations_long

# %% Plots
p = (
    ggplot(durations_long)
    + aes(x='duration_ms', color='label')
    + stat_ecdf(alpha=0.8)
    + facet_wrap('provider', scales = 'free_x', nrow=2)
    + theme(
        subplots_adjust={'hspace': 0.55, 'wspace': 0.02}
    )
)
p.save(path=f"{plots_path}", filename=f"trigger_latency.pdf")
