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
trigger_list = ["All triggers", "http", "storage", "queue",
                "database", "eventHub", "eventGrid", "serviceBus", "timer"]
terminal_menu = TerminalMenu(trigger_list)
menu_entry_index = terminal_menu.show()

if(menu_entry_index == 0):
    trigger_list = ["http", "storage", "queue",
                    "database", "eventHub", "eventGrid", "serviceBus", "timer"]
else:
    trigger_list = [trigger_list[menu_entry_index]]

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
    str(end_date) + "T" + str(end_time) + "Z"

application_ID = INSIGHTS_APP_ID
api_key = INSIGHTS_API_KEY
##

headers = {'x-api-key': api_key, }

print('')
print('Fetching Dependencies...')
dependencies = requests.get('https://api.applicationinsights.io/v1/apps/' +
                            application_ID + '/query?query=dependencies | where name contains "CompletionTrack" or name contains "Custom operationId" or name contains "GET /api/HttpTrigger" | where timestamp between(datetime("' + start_date + " " + start_time + '") .. datetime("' + end_date + " " + end_time + '"))', headers=headers)
dependencies = dependencies.json()

print('')
print('Fetching Traces...')
traces = requests.get('https://api.applicationinsights.io/v1/apps/' +
                      application_ID + '/query?query=traces | where message has "iterationId" | where timestamp between(datetime("' + start_date + " " + start_time + '") .. datetime("' + end_date + " " + end_time + '"))', headers=headers)
traces = traces.json()

for trigger_type in trigger_list:
    invoke_order = []
    execute_order = []

    invoke_duplicates = []
    execute_duplicates = []

    print('## TRIGGER TYPE:' + trigger_type.upper())
    print('Extracting Invoking order...')
    invoke_amount = 0
    execute_amount = 0

    for value in dependencies["tables"][0]["rows"]:
        if("custom operationid " + trigger_type.lower() in value[4].lower()):
            execute_amount = execute_amount + 1
            timestamp = value[0]
            timestamp = timestamp.replace('T', ' ')
            timestamp = timestamp.replace('Z', '')
            operation_id = value[1]
            execute_duplicates.append(value[5])
            d = {}
            d['timestamp'] = timestamp
            d['operation_id'] = operation_id
            execute_order.append(d)
        elif "completiontrack" + trigger_type.lower() in value[4].lower():
            invoke_amount = invoke_amount + 1
            timestamp = value[0]
            timestamp = timestamp.replace('T', ' ')
            timestamp = timestamp.replace('Z', '')
            milli = (timestamp + ".").split(".")[1] + "000"
            timestamp = timestamp.split(".")[0] + "." + milli[0:3]
            name = value[4]
            operation_id = value[14]
            d = {}
            d['timestamp'] = timestamp
            d['operation_id'] = operation_id
            invoke_order.append(d)
        elif trigger_type.lower() == "http" and "GET /api/HttpTrigger".lower() in value[4].lower():
            invoke_amount = invoke_amount + 1
            timestamp = value[0]
            timestamp = timestamp.replace('T', ' ')
            timestamp = timestamp.replace('Z', '')
            milli = (timestamp + ".").split(".")[1] + "000"
            timestamp = timestamp.split(".")[0] + "." + milli[0:3]
            name = value[4]
            operation_id = value[14]
            d = {}
            d['timestamp'] = timestamp
            d['operation_id'] = operation_id
            invoke_order.append(d)

    invoke_order.sort(key=lambda x: x['timestamp'])

    temp_list = []

    for invoke in invoke_order:
        temp_list.append(invoke['operation_id'])
    invoke_order.clear()
    invoke_order = temp_list.copy()

    print('')
    print('Extracting Executing order...')
    for value in traces["tables"][0]["rows"]:
        message_whole = value[1]

        if 'iterationId' + trigger_type.lower() in message_whole:
            invoke_duplicates.append(json.loads(value[4])['iterationId'])

    # Sort by timestamp, must be done before switching operation ids
    execute_order.sort(key=lambda x: x['timestamp'])

    temp_list.clear()
    for execute in execute_order:
        temp_list.append(execute['operation_id'])
    execute_order.clear()
    execute_order = temp_list.copy()

    invoke_duplicates_amount = 0
    for invoke in invoke_duplicates:
        if 1 < invoke_order.count(invoke):
            invoke_duplicates_amount = invoke_duplicates_amount + 1

    execute_duplicates_amount = 0
    for execute in execute_duplicates:
        if 1 < execute_order.count(execute):
            execute_duplicates_amount = execute_duplicates_amount + 1

    missing_executes = []

    for invoke in invoke_order:
        if invoke not in execute_order:
            missing_executes.append(invoke)

    for value in missing_executes:
        while(value in invoke_order):
            invoke_order.remove(value)

    count = -1
    out_of_order = 0
    for invoke in invoke_order:
        count = count + 1
        if invoke != execute_order[count]:
            out_of_order = out_of_order + 1
            if invoke in execute_order:
                execute_order.remove(invoke)
                execute_order.insert(count, invoke)

    print('')
    print('## Results ' + trigger_type + ' ##')
    print('')
    print('Original amount of invokes: ' + str(invoke_amount))
    print('Original amount of executes: ' + str(execute_amount))
    print('')
    print('Contains Duplicates')
    print('Invoke: ' + str(invoke_duplicates_amount))
    print('Execute: ' + str(execute_duplicates_amount))
    print('')
    print('Missing executes: ' + str(len(missing_executes)))
    print('')
    print('Out of order: ' + str(out_of_order))
    print('')
    with open("./../results/reliability/" + trigger_type + '.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["trigger_type", "original_invokes", "original_executes", "duplicates_invokes",
                        "duplicates_executes", "missing_executes", "out_of_order", "amount_invokes_after", "amount_executes_after"])
        writer.writerow([trigger_type, invoke_amount, execute_amount, invoke_duplicates_amount/invoke_amount,
                        execute_duplicates_amount/execute_amount, len(missing_executes)/invoke_amount, out_of_order/invoke_amount, len(invoke_order), len(execute_order)])
    print('')
    print('')
    print('')
