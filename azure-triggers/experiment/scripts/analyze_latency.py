from cgitb import reset
from tracemalloc import start
import requests
import json
from itertools import groupby
from datetime import datetime
import csv
import re
import os
from dotenv import load_dotenv
from datetime import date
from datetime import timedelta
from simple_term_menu import TerminalMenu

load_dotenv('./../../.env')

print("Which trigger should be analyzed?")
trigger_pick = ["All triggers", "http", "storage", "queue",
                "database", "eventHub", "eventGrid", "serviceBus", "timer"]
terminal_menu = TerminalMenu(trigger_pick)
menu_entry_index = terminal_menu.show()

trigger_list = [["http", "GET /api/HttpTrigger"], ["storage", "Azure.Storage.Blob.BlockBlobClient-upload"], ["queue", "Azure.Storage.Queue.QueueClient-sendMessage"],
                ["database", "POST"], ["eventHub", "POST"], ["eventGrid", "Azure.Storage.Blob.BlockBlobClient-upload"], ["serviceBus", ""], ["timer", ""]]

if(menu_entry_index != 0):
    trigger_list = [trigger_list[menu_entry_index-1]]

print("Which start date?")
start_date = [str(date.today() - timedelta(days=1)), str(date.today())]
terminal_menu = TerminalMenu(start_date)
menu_entry_index = terminal_menu.show()
start_date = start_date[menu_entry_index]

print("Does start time matter?")
yes_no = ["No", "Yes"]
terminal_menu = TerminalMenu(yes_no)
answer = terminal_menu.show()

if(yes_no[answer] == "Yes"):
    start_time = input("Write start time (HH:MM:SS): ")
else:
    start_time = "01:00:00"


print("Should end date/time be current time?")
yes_no = ["Yes", "No"]
terminal_menu = TerminalMenu(yes_no)
answer = terminal_menu.show()

if(yes_no[answer] == "Yes"):
    end_date = str(date.today() + timedelta(days=1))
    end_time = "01:00:00"
else:
    print("Which end date?")
    end_date = [str(date.today()), str(date.today() - timedelta(days=1)),
                str(date.today() - timedelta(days=2))]
    terminal_menu = TerminalMenu(end_date)
    menu_entry_index = terminal_menu.show()
    end_time = input("Write end time (HH:MM:SS): ")


INSIGHTS_API_KEY = os.getenv('INSIGHTS_API_KEY')
INSIGHTS_APP_ID = os.getenv('INSIGHTS_APP_ID')

timespan = str(start_date) + "T" + str(start_time) + "Z/" + \
    str(end_date) + "T" + str(end_time) + "Z"  # Time zone GMT
# Azure Insights REST API limits to 500 rows by default, many invocations => thousands of rows. Get top 5000 rows
application_ID = INSIGHTS_APP_ID
api_key = INSIGHTS_API_KEY
##

headers = {'x-api-key': api_key, }

print('')
print('Fetching Requests...')
reqs = requests.get('https://api.applicationinsights.io/v1/apps/' +
                    application_ID + '/query?query=requests | where timestamp between(datetime("' + start_date + " " + start_time + '") .. datetime("' + end_date + " " + end_time + '"))', headers=headers)

reqs = reqs.json()

print('')
print('Fetching Dependencies...')
dependencies = requests.get('https://api.applicationinsights.io/v1/apps/' +
                            application_ID + '/query?query=dependencies | where timestamp between(datetime("' + start_date + " " + start_time + '") .. datetime("' + end_date + " " + end_time + '"))', headers=headers)
dependencies = dependencies.json()

print('')
print('Fetching Traces...')
traces = requests.get('https://api.applicationinsights.io/v1/apps/' +
                      application_ID + '/query?query=traces | where customDimensions contains "Coldstart" | where timestamp between(datetime("' + start_date + " " + start_time + '") .. datetime("' + end_date + " " + end_time + '"))', headers=headers)
traces = traces.json()
all_entries = []
switch_operation_ids = []

print('')
print('Extracting Requests...')

for value in reqs["tables"][0]["rows"]:
    timestamp = value[0]
    timestamp = timestamp.replace('T', ' ')
    timestamp = timestamp.replace('Z', '')
    milli = (timestamp + ".").split(".")[1] + "000"
    timestamp = timestamp.split(".")[0] + "." + milli[0:3]
    name = json.loads(value[10])["FullName"]
    operation_id = value[13]
    d = {}
    d['type'] = 'REQUEST'
    d['name'] = name
    d['timestamp'] = timestamp
    d['operation_id'] = operation_id
    all_entries.append(d)

print('')
print('Extracting Dependencies...')
for value in dependencies["tables"][0]["rows"]:
    if("Custom operationId" in value[4]):
        switch_operation_ids.append([value[1], value[5]])
    else:
        timestamp = value[0]
        timestamp = timestamp.replace('T', ' ')
        timestamp = timestamp.replace('Z', '')
        milli = (timestamp + ".").split(".")[1] + "000"
        timestamp = timestamp.split(".")[0] + "." + milli[0:3]
        name = value[4]
        operation_id = value[14]
        if(name.startswith('POST')):
            name = 'POST'
        d = {}
        d['type'] = 'DEPENDENCY'
        d['name'] = name
        d['timestamp'] = timestamp
        d['duration'] = value[8]
        d['operation_id'] = operation_id
        print(operation_id)
        all_entries.append(d)

print('')
print('Extracting Traces...')
for value in traces["tables"][0]["rows"]:
    custom_dimensions = json.loads(value[4])
    d = {}
    d['type'] = 'TRACE'
    d['name'] = 'Cold start'
    d['timestamp'] = timestamp
    d['operation_id'] = value[7]
    print(value[7])
    all_entries.append(d)

# Sort by timestamp, must be done before switching operation ids
all_entries.sort(key=lambda x: x['timestamp'])

# Switch operation ids if necessary
print('')
print('Setting correct operation IDs...')

if len(switch_operation_ids) > 0:
    for entry in all_entries:
        for switch in switch_operation_ids:
            if entry['operation_id'] == switch[1]:
                entry['operation_id'] = (
                    switch[0].replace('|', '').split('.')[0])


# Remove entries without operation_id
filtered_entries = all_entries.copy()
for entry in filtered_entries:
    if entry['operation_id'] == '':
        filtered_entries.remove(entry)

all_entries = filtered_entries

dash = '-' * 119

# Sort by operation_id before grouping
all_entries.sort(key=lambda x: x['operation_id'])

print('')
print('Partitioning groups...')

all_groups = []
saved_id = None
index = -1
requestCount = 0

for entry in all_entries:
    if saved_id != entry['operation_id']:  # New Group
        requestCount = 0  # Reset count
        if(entry['type'] == 'REQUEST'):
            requestCount += 1
        index += 1
        all_groups.append([])
        all_groups[index].append(entry)
        saved_id = entry['operation_id']
    elif saved_id == entry['operation_id']:
        if(requestCount == 2):
            pass
        else:
            if(entry['type'] == 'REQUEST'):
                requestCount += 1
            all_groups[index].append(entry)


for trigger_type in trigger_list:
    print('Analyzes latency for ' + trigger_type[0])
    print('Checking the validity of traces...')

    all_valid_groups = []

    for group in all_groups:
        trace_amount = 0
        request_amount = 0
        dependency_amount = 0
        # print('')
        isValidRequest = False
        for entry in group:
            if entry['type'] == 'REQUEST':
                request_amount += 1
                isValidRequest = trigger_type[0].lower(
                ) in entry['name'].lower()
                # print(f"{request_amount} - request {entry['name']}")
        if (request_amount == 2 and isValidRequest):
            all_valid_groups.append(group)

    print('')
    print('Checks completed')

    all_trigger_delays_ms = []

    for group in all_valid_groups:
        dependency_timestamp = datetime.now()
        request_timestamp = datetime.now()
        for entry in group:
            if entry['type'] == 'DEPENDENCY':
                dependency_timestamp = datetime.strptime(
                    entry['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
            elif entry['type'] == 'REQUEST' and entry['name'] != 'Functions.InfraEndpoint':
                request_timestamp = datetime.strptime(
                    entry['timestamp'], '%Y-%m-%d %H:%M:%S.%f')

        delta = request_timestamp - dependency_timestamp
        # print(f"{request_timestamp}\n")
        # print(f"{dependency_timestamp}\n")
        # print(f"{delta}\n")
        all_trigger_delays_ms.append(
            (delta.seconds*1000000 + delta.microseconds) / 1000)

    print('')
    print('## RESULTS ' + trigger_type[0].upper() + " ##")
    print('')
    print(all_trigger_delays_ms)
    print('')
    print('Average: ' + str(sum(all_trigger_delays_ms) /
                            max(1, len(all_trigger_delays_ms))) + ' ms')
    print('')
    print('Number of valid entries: ' + str(len(all_trigger_delays_ms)))
    print('')

    with open("./../results/latency/" + trigger_type[0] + '.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["trigger_type", "latency"])
        count = 0
        for value in all_trigger_delays_ms:
            writer.writerow([trigger_type[0], value])
            count = count + 1

    print('')
    print('')
    print('')
