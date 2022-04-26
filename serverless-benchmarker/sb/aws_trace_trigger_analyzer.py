import json
from pathlib import Path
from datetime import datetime
import csv
import re
from sb.aws_trace_analyzer import parse_trace_segments
import logging


NUM_RECEIVER_TIMESTAMPS = 5
# Name of custom trace property to correlate disconnected traces.
# Regex search template for extracting the root trace id
SEARCH_ROOT_TRACE_ID = r'\\"root_trace_id\\":\\"(\d-[a-z0-9]{8}-[a-z0-9]{24})'
SEARCH_ROOT_TRACE_ID_COMPILED = re.compile(SEARCH_ROOT_TRACE_ID)
SEARCH_TRACE_ID = r'^{"Id":\s?"(\d-[a-z0-9]{8}-[a-z0-9]{24})"'
SEARCH_TRACE_ID_COMPILED = re.compile(SEARCH_TRACE_ID)


def extract_root_trace_id(trace_line) -> str:
    """Extracts the root trace id from the raw trace string.
    Searching with a pre-compiled regex is much faster than
    parsing the nested trace JSON (e.g., 30ms regex vs 361ms json).
    """
    match = SEARCH_ROOT_TRACE_ID_COMPILED.search(trace_line)
    if match:
        found = match.group(1)
        return found
    return None


def extract_trace_id(trace_line) -> str:
    """Extracts the trace id from the raw trace string.
    Substring would be faster but potentially less robust."""
    match = SEARCH_TRACE_ID_COMPILED.search(trace_line)
    if match:
        found = match.group(1)
        return found
    return None


# MAYBE: Idea for generic merging using networkx:
# 1) Create parent tree
# 2) Fill child tree but replace its trace_id with the "parent_trace_id"
# 3) Link them together either by:
#    a) using "parent_id" or
#    b) by leveraging some application knowledge
# MAYBE: Idea for generic merging of trace documents:
# 1) Replace trace_id everywhere in child_segments
# 2) Add "parent_id" to first document in child trace without parent_id
#    (e.g., 40cfcf43ef5ae6ab in Queue example from 2022-04-01_01-11-31)
# 3) Update duration with as rounded timediff between earliest and latest timestamp
def merge_and_analyze_traces(parent_line, child_line) -> dict():
    """Merges two disconnected traces into a single parsed trace document.
    Notice that the subsegments are already parsed unlike the traces from the API.
    """
    parent_trace = json.loads(parent_line)
    parent_segments = parse_trace_segments(parent_trace)
    child_trace = json.loads(child_line)
    child_segments = parse_trace_segments(child_trace)

    acc = dict()
    acc['root_trace_id'] = parent_trace.get('Id')
    acc['child_trace_id'] = child_trace.get('Id')
    for segment in child_segments:
        acc = extract_result(segment, acc)
        acc = search_subsegments_rec(segment, acc)

    for segment in parent_segments:
        acc = extract_result(segment, acc)
        acc = search_subsegments_rec(segment, acc)

    return acc


def analyze_trace(line) -> dict():
    """Analyzes a single trace line."""
    trace = json.loads(line)
    segments = parse_trace_segments(trace)

    acc = dict()
    acc['root_trace_id'] = trace.get('Id')
    for segment in segments:
        acc = extract_result(segment, acc)
        acc = search_subsegments_rec(segment, acc)

    return acc


def search_subsegments_rec(segment, acc):
    """Recursively searches segments and subsegments."""
    if 'subsegments' in segment:
        for subsegment in segment['subsegments']:
            acc = extract_result(subsegment, acc)
            acc = search_subsegments_rec(subsegment, acc)
    return acc


def extract_result(segment, acc):
    """Adds any relevant timestamp from the given
    segment or subsegment to the result dictionary acc.
    """
    if 'name' in segment:
        if segment['name'].endswith('_trigger'):
            # Function1: Before service call
            acc['t1'] = ts(segment['start_time'])
            # Function1: After service call
            # NOTE: This timestamp might in some circumstances
            # occur after the Lambda `Invocation` segment.
            # This happened for the queue trigger execution "2022-04-03_22-07-41".
            # This might be related to the usage of `.finalize()`
            acc['t2'] = ts(segment['end_time'])
        if 'origin' in segment and segment['origin'] == 'AWS::Lambda' \
                and 'TriggerLambda' in segment['name']:
            # Function2: infrastructure
            acc['t3'] = ts(segment['start_time'])
        if segment['name'] == 'receiver0':
            # Function2: first LOC
            acc['t4'] = ts(segment['start_time'])
        for n in range(1, NUM_RECEIVER_TIMESTAMPS + 1):
            if segment['name'] == f"receiver{n}":
                acc[f"t{n+4}"] = ts(segment['start_time'])
        # Detect coldstarts
        if 'origin' in segment and segment['origin'] == 'AWS::Lambda::Function' \
                and segment['name'].startswith('InfraLambda'):
            # Function1: coldstart flag
            acc['coldstart_f1'] = is_coldstart(segment)
        if 'origin' in segment and segment['origin'] == 'AWS::Lambda::Function' \
                and 'TriggerLambda' in segment['name']:
            # Function2: coldstart flag
            acc['coldstart_f2'] = is_coldstart(segment)
    if segment.get('in_progress'):
        raise Exception(f"Segment {segment.get('id')} in progress.")
    if segment.get('error'):
        raise Exception(f"Segment {segment.get('id')} has an error.")

    return acc


def ts(unix_timestamp) -> datetime:
    """Converts a unix timestamp into a Python datetime object."""
    f = float(unix_timestamp)
    return datetime.utcfromtimestamp(f)


def is_coldstart(segment) -> bool:
    """Returns True if the given Lambda function contains an Initialization subsegment
    and False otherwise.
    * segment: must be of origin 'AWS::Lambda::Function'
    """
    if 'subsegments' in segment:
        for subsegment in segment['subsegments']:
            if subsegment.get('name') == 'Initialization':
                return True
    return False


# TODO: Add unit tests. Suggested execution: 2022-04-01_01-11-31
class AwsTraceTriggerAnalyzer:
    """Parses traces.json files downloaded by the AwsTraceDownloader:
    1) Saves a trace trigger summary into trigger.csv
    2) Saves a log of invalid trace into trigger_invalid_traces.csv

    Limitation: This analyzer is not generic. It expects a custom trace
    with two Lambda functions where Function1 (F1) triggers Function2 (F2)
    through an external service either synchronously (e.g., API Gateway) or
    asynchronously (e.g., S3). It further expects custom trace logs with
    timestamps following a specific trace model and custom trace annotations
    for correlating disconnected traces through a common `root_trace_id`.
    """

    def __init__(self, log_path) -> None:
        self.log_path = log_path

    def analyze_traces(self):
        file = Path(self.log_path)
        trigger_file = file.parent / 'trigger.csv'
        invalid_file = file.parent / 'trigger_invalid_traces.csv'

        # Dictionary: trace_id (str) => parent trace payload (str)
        # for caching unmatched parent traces. This typically refers to
        # the upstream trace of Function1.
        parents = dict()
        # Dictionary: parent_trace_id (str) => child trace payload (str)
        # for caching unmatched child traces index by the parent trace id.
        # This typically refers to the downstream trace of Function2.
        children = dict()
        num_valid_traces = 0
        num_invalid_traces = 0
        with open(file, 'r') as traces_json, \
             open(trigger_file, 'w') as traces_csv, \
             open(invalid_file, 'w') as invalid_csv:

            receiver_timestamps = [f"t{n+4}" for n in range(1, NUM_RECEIVER_TIMESTAMPS + 1)]
            trace_headers = ['root_trace_id', 'child_trace_id', 't1', 't2', 't3', 't4',
                             *receiver_timestamps,
                             'coldstart_f1', 'coldstart_f2']
            trace_writer = csv.DictWriter(traces_csv, quoting=csv.QUOTE_MINIMAL,
                                          fieldnames=trace_headers)
            trace_writer.writeheader()
            invalid_writer = csv.writer(invalid_csv, quoting=csv.QUOTE_MINIMAL)
            invalid_headers = ['trace_id', 'message']
            invalid_writer.writerow(invalid_headers)
            for line in traces_json:
                try:
                    root_trace_id = extract_root_trace_id(line)
                    if root_trace_id:  # child trace
                        if root_trace_id in parents:
                            # logging.debug('Found matching parent for this child trace.')
                            trigger = merge_and_analyze_traces(parents[root_trace_id], line)
                            trace_writer.writerow(trigger)
                            num_valid_traces += 1
                            del parents[root_trace_id]
                        else:
                            children[root_trace_id] = line
                    else:  # parent trace
                        trace_id = extract_trace_id(line)
                        if trace_id in children:
                            # logging.debug('Found matching child for this parent trace.')
                            trigger = merge_and_analyze_traces(line, children[trace_id])
                            trace_writer.writerow(trigger)
                            num_valid_traces += 1
                            del children[trace_id]
                        else:
                            parents[trace_id] = line
                except Exception as e:
                    trace_id = extract_trace_id(line)
                    message = str(e)
                    invalid_writer.writerow([trace_id, message])
                    num_invalid_traces += 1

            # Analyze fully connected traces (i.e., no children found)
            if len(parents) > 0:
                for trace_line in parents.values():
                    try:
                        trigger = analyze_trace(trace_line)
                        trace_writer.writerow(trigger)
                        num_valid_traces += 1
                    except Exception as e:
                        trace_id = extract_trace_id(line)
                        message = str(e)
                        invalid_writer.writerow([trace_id, message])
                        num_invalid_traces += 1

        logging.info(f"Analyzed {num_valid_traces} valid trigger traces. Written to {trigger_file}.")  # noqa: E501
        if num_invalid_traces > 0:
            invalid_rate = round(num_invalid_traces / (num_valid_traces + num_invalid_traces) * 100, 2)  # noqa: E501
            logging.warning(f"Detected {num_invalid_traces} ({invalid_rate}%) invalid traces. Written to {invalid_file}.")  # noqa: E501
