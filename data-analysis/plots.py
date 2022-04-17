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

# Check for negative timediffs
if not durations_long[durations_long['duration_ms']<0].empty:
    neg_durations = durations_long[durations_long['duration_ms']<0]
    logging.warning(f"Found {len(neg_durations)} timediffs with negative duration. Check `neg_duration`!")
    # Option to filter them out if these are non-problematic exceptional occurrences
    # durations_long = durations_long.drop(durations_long[durations_long['duration_ms']<0].index)

# Rename and reorder categories
durations_long['trigger'] = durations_long['trigger'].map(TRIGGER_MAPPINGS)
durations_long['trigger'] = pd.Categorical(durations_long['trigger'],
                                            categories=TRIGGER_MAPPINGS.values(),
                                            ordered=True)
durations_long['provider'] = durations_long['provider'].map(PROVIDER_MAPPINGS)
durations_long['provider'] = pd.Categorical(durations_long['provider'],
                                            categories=PROVIDER_MAPPINGS.values(),
                                            ordered=True)
durations_long['duration_type'] = durations_long['duration_type'].map(DURATION_MAPPINGS)
durations_long['duration_type'] = pd.Categorical(durations_long['duration_type'],
                                            categories=DURATION_MAPPINGS.values(),
                                            ordered=True)

# %% Plots
p = (
    ggplot(durations_long)
    + aes(x='duration_ms', color='trigger')
    + stat_ecdf(alpha=0.8)
    + facet_wrap('provider', scales = 'free_x', nrow=2)
    + theme(
        subplots_adjust={'hspace': 0.55, 'wspace': 0.02}
    )
)
p.save(path=f"{plots_path}", filename=f"trigger_latency.pdf")

# %%
