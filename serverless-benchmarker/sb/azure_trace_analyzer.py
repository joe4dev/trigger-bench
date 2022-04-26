import logging
import json
from pathlib import Path
import csv
import pandas as pd
from sb.azure_trace_downloader import convert_insights_json_to_df


# Number of additional timestamps in Function2
NUM_RECEIVER_TIMESTAMPS = 5


def extract_trigger_results(trace) -> dict:
    """Returns a dictionary of timestamps and metadata for a trace data frame.
    Parameters:
    * trace: Pandas data frame with Azure Insight tables and
          additional attributes 'rootTraceId' and 'traceId'
          (see azure_trace_downloader.py for explanation)
    Process:
    1) Identify the relevant timestamps for trigger time
    2) Identify coldstarts
    Limitation: The current implementation does not perform any additional validation.
    """
    result = dict()
    rootTraceId = trace.attrs['rootTraceId']
    result['root_trace_id'] = rootTraceId
    traceId = trace.attrs['traceId']
    result['child_trace_id'] = traceId
    # We use the dependency name f"{trigger_type}_trigger" (e.g., eventHub_trigger)
    # in custom .trackDependency() instrumentation to indicate the outgoing service call
    # that triggers another function. This applies for both, sync and async triggers.
    # IMPORTANT: Before the service call, we capture a startTime and after the service call
    # we use .trackDependency() to report completion. This might be counter-intuitive because
    # the timestamp from the instrumentation is actually the endTime and the duration is
    # the time between startTime (t1) and endTime (t2).
    service_call = trace.loc[(trace['itemType'] == 'dependency') & (trace['name'].str.endswith('_trigger'))]  # noqa: E501
    result['t1'] = pd.to_datetime(service_call['timestamp'].item()) - pd.Timedelta(microseconds=service_call['duration'].item() * 1000)  # noqa: E501
    # duration is in milliseconds (ms)
    result['t2'] = pd.to_datetime(service_call['timestamp'].item())
    # NOTE: operationId-based matching fails for connected traces.
    # For example, HTTP requests properly propagate trace ids and
    # therefore form fully connected traces.
    # Therefore, the following comparison would be unreliable: (df['operation_Id'] == traceId)
    function2_request = trace.loc[(trace['itemType'] == 'request') & (trace['name'].str.endswith('Trigger'))]  # noqa: E501
    t3_sub_ms = pd.to_datetime(function2_request['timestamp'].item())
    # We have to remove the microseconds for t3 to standardize the time formats because
    # t3 has nanosecond precision in comparison to all other timestamps with ms-precision.
    result['t3'] = t3_sub_ms - pd.Timedelta(microseconds=t3_sub_ms.microsecond % 1000,
                                            nanoseconds=t3_sub_ms.nanosecond)
    function2_code = trace.loc[(trace['itemType'] == 'dependency') & (trace['name'] == 'receiver0')]  # noqa: E501
    result['t4'] = pd.to_datetime(function2_code['timestamp'].item())

    for n in range(1, NUM_RECEIVER_TIMESTAMPS + 1):
        receiver_n = trace.loc[(trace['itemType'] == 'dependency') & (trace['name'] == f"receiver{n}")]  # noqa: E501
        result[f"t{n+4}"] = pd.to_datetime(receiver_n['timestamp'].item())

    # Identify cold starts
    result['coldstart_f1'] = not trace[(trace['operation_Id'] == rootTraceId) & (trace['itemType'] == 'trace') & (trace['customDimensions'].str.contains('ColdStart'))].empty  # noqa: E501
    result['coldstart_f2'] = not trace[(trace['operation_Id'] == traceId) & (trace['itemType'] == 'trace') & (trace['customDimensions'].str.contains('ColdStart'))].empty  # noqa: E501

    return result


# TODO: Unify naming with AWS trigger => clarify that for TriggerBench
class AzureTraceAnalyzer:
    """Parses traces.json files downloaded by the AzureTraceDownloader:
    1) Saves a trigger results summary into `trigger.csv`
    Limitation: A generic breakdown analyzer is currently not implemented.
    """

    def __init__(self, log_path) -> None:
        self.log_path = log_path

    def analyze_traces(self):
        file = Path(self.log_path)
        # breakdown_file = file.parent / 'trace_breakdown.csv'
        invalid_file = file.parent / 'invalid_traces.csv'
        trigger_file = file.parent / 'trigger.csv'

        num_valid_traces = 0
        num_invalid_traces = 0
        with open(file, 'r') as traces_json, \
             open(trigger_file, 'w') as trigger_csv, \
             open(invalid_file, 'w') as invalid_csv:
            receiver_timestamps = [f"t{n+4}" for n in range(1, NUM_RECEIVER_TIMESTAMPS + 1)]
            trace_headers = ['root_trace_id', 'child_trace_id', 't1', 't2', 't3', 't4',
                             *receiver_timestamps,
                             'coldstart_f1', 'coldstart_f2']
            trace_writer = csv.DictWriter(trigger_csv, quoting=csv.QUOTE_MINIMAL,
                                          fieldnames=trace_headers)
            trace_writer.writeheader()
            invalid_writer = csv.writer(invalid_csv, quoting=csv.QUOTE_MINIMAL)
            invalid_headers = ['root_trace_id', 'receiver_trace_id', 'message']
            invalid_writer.writerow(invalid_headers)
            for index, line in enumerate(traces_json):
                try:
                    trace = json.loads(line)
                    df = convert_insights_json_to_df(trace)
                    # Export csv version of df (without attrs) for debugging
                    # DEBUG: Write to CSV for easier inspection
                    # trace_raw_file = file.parent / f"trace_{index}.csv"
                    # df.to_csv(trace_raw_file, index=False)
                    # Export trigger results
                    trigger_results = extract_trigger_results(df)
                    trace_writer.writerow(trigger_results)
                    num_valid_traces += 1
                except Exception as e:
                    invalid_row = [trace['attrs'].get('rootTraceId'), trace['attrs'].get('traceId'), str(e)]  # noqa: E501
                    invalid_writer.writerow(invalid_row)
                    num_invalid_traces += 1

        logging.info(f"Analyzed {num_valid_traces} valid trigger traces. Written to {trigger_file}.")  # noqa: E501
        if num_invalid_traces > 0:
            invalid_rate = round(num_invalid_traces / (num_valid_traces + num_invalid_traces) * 100, 2)  # noqa: E501
            logging.warning(f"Detected {num_invalid_traces} ({invalid_rate}%) invalid traces. Written to {invalid_file}.")  # noqa: E501
