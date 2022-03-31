import json
from pathlib import Path
from itertools import groupby
from datetime import datetime
import csv
import os
import re

# EDIT THIS PARAMETER
trigger_type = 'queue'

valid_traces = []
invalid_traces = []
switch_trace_ids = []

def parse_segment_json(segment_wrapper):
    return json.loads(segment_wrapper['Document'])

# TODO Check sb_config.yml to check trigger type
log_folders = Path('../logs/') # Cleanup log folder before running, don't mix triggers
for folder in log_folders.iterdir():
    for file in folder.iterdir():
        if file.name == 'traces.json':
            with open(file) as json_file:
                traces = json.load(json_file)
                for trace in traces.values():
                    # Check if it is a complete and valid trace
                    if 'Duration' not in trace:
                        invalid_traces.append(trace)
                        continue
                    else:
                        segments = list(map(lambda s: parse_segment_json(s), trace['Segments']))
                        for segment in segments:
                            origin = segment['origin']
                            timestamp = segment['start_time'] * 1000 # Convert to ms
                            timestamp = str(datetime.fromtimestamp(timestamp / 1000.0))
                            name = segment['name']
                            trace_id = segment['trace_id']
                            d = {}
                            d['type'] = origin
                            d['name'] = name
                            d['timestamp'] = timestamp
                            d['trace_id'] = trace_id
                            if 'subsegments' in segment:
                                # Handle swapping of trace ids in Queue trigger
                                for subsegment in segment['subsegments']:
                                    if 'subsegments' in subsegment:
                                        annotation = list(filter(lambda s: s['name'] == 'Annotations', subsegment['subsegments']))
                                        if len(annotation) > 0:
                                            annotation = annotation[0]
                                            new_trace_id = annotation['annotations']['AWSTraceHeader']
                                            switch_trace_ids.append({'oldTraceId': trace['Id'], 'newTraceId': new_trace_id})
                                d['subsegments'] = segment['subsegments']
                            valid_traces.append(d)


# Sort by timestamp
valid_traces.sort(key=lambda x:x['timestamp'])

# Switch trace ids if necessary
print('')
print('Setting correct trace IDs...')

if len(switch_trace_ids) > 0:
    for i, entry in enumerate(valid_traces):
        for switch in switch_trace_ids:
            if entry['trace_id'] == switch['oldTraceId']:
                entry['trace_id'] = switch['newTraceId']

# Sort by trace_id and partition groups
valid_traces.sort(key=lambda x:x['trace_id'])

print('')
print('Partitioning groups...')

all_groups = []
saved_id = ''
index = -1

for entry in valid_traces:
    if saved_id != entry['trace_id']:
        index += 1
        all_groups.append([])
        all_groups[index].append(entry)
        saved_id = entry['trace_id']
    else:
        all_groups[index].append(entry)

print('')
print('Checking the validity of traces...')

all_valid_groups = []

for group in all_groups:
    infra_amount = 0
    http_amount = 0
    storage_amount = 0
    queue_amount = 0
    for entry in group:
        if 'Infra' in entry['name']:
            infra_amount += 1
        elif 'HTTP' in entry['name']:
            http_amount += 1
        elif 'Storage' in entry['name']:
            storage_amount += 1
        elif 'Queue' in entry['name']:
            queue_amount += 1
    if infra_amount >= 3 and (http_amount == 3 or storage_amount == 2 or queue_amount == 2):
        all_valid_groups.append(group)
    else:
        print('Group with id ' + str(group[0]['trace_id']) + ' was thrown out...')

all_groups = all_valid_groups

# Calculate trigger latencies
all_trigger_delays_ms = []

for group in all_groups:
    dependency_timestamp = None
    trigger_start_timestamp = None
    valid_group = True
    for entry in group:
        # Infrastructure
        if entry['type'] == 'AWS::Lambda::Function' and 'Infra' in entry['name']:
            invocation_subsegment = list(filter(lambda s: s['name'] == 'Invocation', entry['subsegments']))
            if len(invocation_subsegment) > 0:
                invocation_subsegment = invocation_subsegment[0]
                dependency_subsegment = invocation_subsegment['subsegments'][0] # First subsegment is the dependency call (HTTP request, S3 or SQS)
                timestamp = dependency_subsegment['start_time'] * 1000 # Convert to ms
                timestamp = str(datetime.fromtimestamp(timestamp / 1000.0))
                if len(timestamp) == 19:
                    # No .%f present
                    timestamp = timestamp + '.00'
                dependency_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
            else:
                valid_group = False
        # HTTP trigger
        elif entry['type'] == 'AWS::ApiGateway::Stage' and 'HTTP' in entry['name']:
            timestamp = entry['timestamp']
            if len(timestamp) == 19:
                # No .%f present
                timestamp = timestamp + '.00'
            trigger_start_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        # Storage trigger
        elif entry['type'] == 'AWS::Lambda' and 'Storage' in entry['name']:
            first_attempt_subsegment = list(filter(lambda s: s['name'] == 'Attempt #1', entry['subsegments']))
            if len(first_attempt_subsegment) > 0:
                first_attempt_subsegment = first_attempt_subsegment[0]
                timestamp = first_attempt_subsegment['start_time'] * 1000 # Convert to ms
                timestamp = str(datetime.fromtimestamp(timestamp / 1000.0))
                if len(timestamp) == 19:
                    # No .%f present
                    timestamp = timestamp + '.00'
                trigger_start_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
            else:
                valid_group = False
        # Queue trigger
        elif entry['type'] == 'AWS::Lambda' and 'Queue' in entry['name']:
            timestamp = entry['timestamp']
            if len(timestamp) == 19:
                # No .%f present
                timestamp = timestamp + '.00'
            trigger_start_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')

    if not trigger_start_timestamp or not dependency_timestamp:
        valid_group = False

    if valid_group:
        delta = trigger_start_timestamp - dependency_timestamp
        all_trigger_delays_ms.append((delta.seconds*1000000 + delta.microseconds) / 1000)
    else:
        print('Group with id ' + str(group[0]['trace_id']) + ' was thrown out...')

print('')
print('Checks completed')

print('')
print('## RESULTS ##')
print('')
print(all_trigger_delays_ms)
print('')
print('Average: ' + str(sum(all_trigger_delays_ms) / max(1, len(all_trigger_delays_ms))) + ' ms')
print('')
print('Number of valid entries: '+ str(len(all_trigger_delays_ms)))
print('')

csvFile = str(datetime.strptime(str(datetime.now()), '%Y-%m-%d %H:%M:%S.%f')).split('.')[0]
csvFile = re.sub(' ', '_', csvFile)
csvFile = re.sub(':', '-', csvFile)
with open(trigger_type + '-' + csvFile + '.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Trigger type: ' + trigger_type])
    writer.writerow(['Traces: ' + str(len(all_trigger_delays_ms))])
    writer.writerow([])
    writer.writerow(['Measured latencies:'])
    for value in all_trigger_delays_ms:
        writer.writerow([value])
