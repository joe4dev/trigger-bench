"""
Generates all plots by loading and analyzing all executions
"""

# %% Imports
import sys
from pathlib import Path
from data_importer import *
from plotnine import *
from mizani.palettes import brewer_pal


# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Optionally overwrite plots path optionally configurable through PLOTS_PATH
plots_path = Path('/Users/joe/Documents/Papers/tex22-trigger-bench-ic2e22/plots')

# %% Load data
execution_paths = find_execution_paths(data_path)
trigger_dfs = []
for execution in execution_paths:
    app_config, app_name = read_sb_app_config(execution)
    trigger = read_trigger_csv(execution)
    trigger['provider'] = parse_provider(app_config)
    trigger['label'] = app_config.get('label', None)
    trigger['trigger'] = app_config.get('trigger', None)
    trigger['burst_size'] = app_config.get('burst_size', None)
    trigger_dfs.append(trigger)

# Combine data frames
traces = pd.concat(trigger_dfs)

# %% Preprocess data
warm_traces = filter_traces_warm(traces)
durations = calculate_durations(warm_traces)
durations_long = pd.melt(durations, id_vars=['root_trace_id', 'child_trace_id', 'provider', 'trigger', 'burst_size', 'label'], var_name='duration_type', value_vars=TIMEDELTA_COLS, value_name='duration')
durations_long['duration_ms'] = durations_long['duration'].dt.total_seconds() * 1000

# Check for negative timediffs
if not durations_long[durations_long['duration_ms']<0].empty:
    neg_durations = durations_long[durations_long['duration_ms']<0]
    logging.warning(f"Found {len(neg_durations)} timediffs with negative duration. Check `neg_duration`!")
    # Option to filter them out if these are non-problematic exceptional occurrences
    # durations_long = durations_long.drop(durations_long[durations_long['duration_ms']<0].index)

# Select trigger times
trigger_latency = durations_long[(durations_long['label'].str.startswith('constant_1rps_60min')) & (durations_long['duration_type'] == 'trigger_time')]
# trigger_latency = trigger_latency[trigger_latency['trigger'] != 'storage']

# TODO: Add baseline as burst size 1
burst_df = durations_long[(durations_long['label'].str.startswith('bursty_3000_invocations')) & (durations_long['duration_type'] == 'trigger_time')]

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

### Plots
# %% Trigger latency plot for Azure
# Aggregate for annotating summary stats
df_agg = df.groupby(['provider', 'trigger']).agg(
    mean_latency=('duration_ms', lambda x: x.mean()),
    p50_latency=('duration_ms', lambda x: x.quantile(0.5)),
    p99_latency=('duration_ms', lambda x: x.quantile(0.99))
)
df_agg = df_agg.reset_index().dropna()
# Write to CSV
# df_agg.to_csv(f"{plots_path}/df_agg.csv")

offset_path = script_dir / 'df_agg_offsets.csv'
df_agg_offsets = pd.read_csv(offset_path)
df_agg = pd.merge(df_agg, df_agg_offsets, on=['provider', 'trigger'], suffixes=('', '_offset'))

def format_labels(breaks):
    return ["{:.0f}".format(l) for l in breaks]
breakdown_colors = ['#fdb462','#80b1d3','#d9ffcf','#bebada','#ffffb3','#8dd3c7', '#fccde5','#b3de69']
linda_colors = ['#D9B466','#EBD9B2','#AED9D6','#5BB4AC','#9A609A','#5B507A', '#74A1CF','#083D77']
custon_brewer_colors = brewer_pal(type='qual', palette=2, direction=1)(8)
p = (
    ggplot(df)
    + aes(x='duration_ms', color='trigger', fill='trigger')
    + stat_ecdf(alpha=0.9)
    # Density plot is hard to tune for visually well-perceivable results
    # + geom_density(aes(y=after_stat('count')),alpha=0.1)
    + geom_vline(df_agg, aes(xintercept='p50_latency', color='trigger'), linetype='dotted', show_legend=False, alpha=0.5)
    # TODO: Fix label placement:
    # a) Some custom x offset if there are not too many overlapping (should work for 2, harder with 3)
    # b) Outside of canvas: https://stackoverflow.com/questions/67625992/how-to-place-geom-text-labels-outside-the-plot-boundary-in-plotnine
    + geom_text(df_agg, aes(label='p50_latency', x='p50_latency+x_offset', y='0.5+y_offset', color='trigger'), format_string='{:.0f}', show_legend=False, size=8)
    + facet_wrap('provider', nrow=2)  # scales = 'free_x'
    + scale_x_log10(labels=format_labels)
    # + xlim(0, 400)
    # + xlim(0, 2000)
    # + xlim(0, 5000)
    # + xlim(0, 10000)
    + scale_color_manual(custon_brewer_colors)
    + labs(x='Latency (ms)', y="Empirical Cumulative Distribution Function (ECDF)", color='Trigger')
    + theme_light(base_size=12)
    + theme(
        # subplots_adjust={'hspace': 0.5}
    )
)
p.save(path=f"{plots_path}", filename=f"trigger_latency.pdf")

# %% Trigger latency plot for different burst sizes
p = (
    ggplot(burst_df)
    + aes(x='duration_ms', color='burst_size')
    + stat_ecdf(alpha=0.8)
    + facet_wrap('~ provider + trigger', scales = 'free_x', nrow=2)
    # + scale_x_log10(labels=format_labels)
    # + xlim(0, 400)
    # + xlim(0, 2000)
    # + xlim(0, 5000)
    # + xlim(0, 10000)
    # TODO: Fix color scheme
    + theme(
        subplots_adjust={'hspace': 0.55, 'wspace': 0.02}
    )
)
p.save(path=f"{plots_path}", filename=f"trigger_latency_by_burst_size.pdf")

# %%
