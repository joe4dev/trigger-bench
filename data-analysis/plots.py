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

# Select trigger times
trigger_latency = durations_long[durations_long['duration_type'] == 'trigger_time']

# %% Rename and reorder categories
df = trigger_latency.copy()
df['trigger'] = df['trigger'].map(TRIGGER_MAPPINGS)
df['trigger'] = pd.Categorical(df['trigger'],
                                categories=TRIGGER_MAPPINGS.values(),
                                ordered=True)
df['provider'] = df['provider'].map(PROVIDER_MAPPINGS)
df['provider'] = pd.Categorical(df['provider'],
                                categories=PROVIDER_MAPPINGS.values(),
                                ordered=True)
df['duration_type'] = df['duration_type'].map(DURATION_MAPPINGS)
df['duration_type'] = pd.Categorical(df['duration_type'],
                                categories=DURATION_MAPPINGS.values(),
                                ordered=True)

# %% Plots
# Aggregate for annotating summary stats
df_agg = df.groupby(['provider', 'trigger']).agg(
    mean_latency=('duration_ms', lambda x: x.mean()),
    p50_latency=('duration_ms', lambda x: x.quantile(0.5)),
    p99_latency=('duration_ms', lambda x: x.quantile(0.99))
)
df_agg = df_agg.reset_index().dropna()
p = (
    ggplot(df)
    + aes(x='duration_ms', color='trigger')
    + stat_ecdf(alpha=0.8)
    + geom_vline(df_agg, aes(xintercept='p50_latency', color='trigger'), linetype='dotted')
    # TODO: Fix label placement:
    # a) Some custom x offset if there are not too many overlapping (should work for 2, harder with 3)
    # b) Outside of canvas: https://stackoverflow.com/questions/67625992/how-to-place-geom-text-labels-outside-the-plot-boundary-in-plotnine
    + geom_text(df_agg, aes(label='p50_latency', x='p50_latency', y=0.8, color='trigger'), format_string='{:.0f}', show_legend=False, size=8)
    + facet_wrap('provider', nrow=2)  # scales = 'free_x'
    + xlim(0, 400)
    + theme(
        subplots_adjust={'hspace': 0.55, 'wspace': 0.02}
    )
)
p.save(path=f"{plots_path}", filename=f"trigger_latency.pdf")

# %%
