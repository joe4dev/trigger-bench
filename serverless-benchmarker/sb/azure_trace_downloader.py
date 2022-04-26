import logging
from datetime import datetime, timezone
import json
import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
import os
from dotenv import load_dotenv


def convert_insights_json_to_df(json_data) -> pd.DataFrame:
    """Converts a JSON response from Azure Insights into a Pandas data frame.
    Raises an exception for errors.
    """
    if 'error' in json_data:
        raise Exception(f"Error in Azure Insights response. {json_data['error'].get('message')}.")
    columns = [x['name'] for x in json_data['tables'][0]['columns']]
    rows = json_data['tables'][0]['rows']
    # NOTE: depends on experimental pandas feature:
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.attrs.html
    df = pd.DataFrame(rows, columns=columns)
    if 'attrs' in json_data:
        df.attrs.update(json_data['attrs'])
    return df


class AzureTraceDownloader:
    """Implements get_traces(self) to download Microsoft Azure Insights traces using
    * Azure Application Insights API Reference: https://docs.microsoft.com/en-us/rest/api/application-insights/query/get    # noqa: E501
    * Kusto Query Language (KQL): https://docs.microsoft.com/en-us/azure/data-explorer/kusto/query/
    * Query best practices: https://docs.microsoft.com/en-us/azure/data-explorer/kusto/query/best-practices  # noqa: E501
    * Telemetry date model: https://docs.microsoft.com/en-us/azure/azure-monitor/app/data-model
    The instrumentation SDKs might be relevant for investigating where the logs are produced:
    * Node.js Insights SDK: https://github.com/microsoft/ApplicationInsights-node.js#readme
    * Dotnet Insights SDK: https://github.com/microsoft/ApplicationInsights-dotnet
    """

    def __init__(self, spec) -> None:
        self.spec = spec
        self.load_credentials()

    def load_credentials(self):
        """Load credentials from environment through .env file
        as used in trigger-bench."""
        env_file = self.spec.logs_directory().parent.parent / '.env'
        load_dotenv(env_file, override=True)
        self.api_app_id = os.environ['INSIGHTS_APP_ID']
        self.api_key = os.environ['INSIGHTS_API_KEY']

    def get_traces(self):
        """Retrieves Azure Insights traces from the last invocation.
        """
        start, end = self.spec.event_log.get_invoke_timespan()
        log_path = self.spec.logs_directory()

        trace_ids_file = log_path.joinpath('trace_ids.txt')
        trace_file = log_path.joinpath('traces.json')

        # MAYBE: Could probably simplify to .isoformat() as described here:
        # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python
        start_time = datetime.fromtimestamp(datetime.timestamp(start), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # noqa: E501
        end_time = datetime.fromtimestamp(datetime.timestamp(end), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # noqa: E501
        experiment_time = f"timestamp between(datetime({start_time}) .. datetime({end_time}))"

        # > Retrieve trace ids

        # MAYBE: Suggestion for implementing and parsing trace correlation data in a generic way.
        # Use standardized W3C `traceparent` to pass trace id and trace parent id rather than
        # some custom format. See: https://www.w3.org/TR/trace-context/#traceparent-header

        # We assume that each receiving function (i.e., Function2) emits a .trackDependency
        # log entry with the name "receiver0" and the data payload containing the root trace id.
        # * data: the root trace id received from the invoker function
        # * operation_Id: the trace id automatically generated for Function2.
        #   For disconnected traces, this trace id differs from the root trace id.
        #   For fully connected traces (e.g., HTTP trigger supports traceparent propagation),
        #   this trace id is identical to the root trace id.
        trace_ids_query = f"""
            dependencies
            | where {experiment_time} and name == "receiver0"
            | project rootTraceId=data, traceId=operation_Id
            """

        # Useful columns for debugging:
        # | project timestamp, customDimensions, sdkVersion, message
        data = self.get_query_result_json(trace_ids_query)
        df = convert_insights_json_to_df(data)
        df.to_csv(trace_ids_file, index=False)

        # Retrieve details for each trace
        with open(trace_file, 'w') as f:
            for rootTraceId, traceId in zip(df['rootTraceId'], df['traceId']):
                # WARNING: This query is computationally very expensive and slow.
                # It would be faster to download everything, potentially for each
                # database separately, and then correlate the traces using pandas.
                # This requires more memory and might require client-side pagination
                # for large datasets.
                # NOTE: This query misses more detailed coldstart traces that are
                # not linked to the operation_Id and would need to be correlated
                # separately through `HostInstanceId` and `ProcessId`.
                trace_query = f"""
                union traces,requests,dependencies
                | where {experiment_time} and
                  (operation_Id == "{rootTraceId}" or operation_Id == "{traceId}" )
                """
                # Potential projection for large subset of fields:
                # | project timestamp,message,itemType,customDimensions,operation_Name,operation_Id,operation_ParentId,client_OS,sdkVersion,itemId,id,name,success,resultCode,duration,performanceBucket,target,type,data  # noqa: E501
                trace = self.get_query_result_json(trace_query)
                trace['attrs'] = {
                    'rootTraceId': rootTraceId,
                    'traceId': traceId
                }
                f.write(json.dumps(trace) + '\n')

        # Inform user
        logging.info(f"Downloaded {len(df)} traces for invocations between \
{start} and {end} into {trace_file}.")

    def retrieve_all_details(self, experiment_time):
        """Retrieves json of all detailed traces available during experiment time without correlation.
        Available dimensions:
        * availabilityResults
        * browserTimings
        * customEvents
        * customMetrics
        * dependencies
        * exceptions
        * pageViews
        * performanceCounters
        * requests
        * traces
        """
        detail_query = f"""
            union requests,dependencies,traces,customMetrics,performanceCounters
            | where {experiment_time}
        """
        return self.get_query_result_json(detail_query)

    def get_query_result_json(self, api_query):
        """Runs an Azure Insights (ai) query and returns the result in json.
        Requires `insights_application_id` and `insights_api_key` in spec."""
        # DEBUG:
        # logging.info(api_query)
        api_version = 'v1'
        api_url = f"https://api.applicationinsights.io/{api_version}/apps/{self.api_app_id}/query?query={api_query}"  # noqa: E501
        headers = {"x-api-key": self.api_key}
        # Configure retry strategy to mitigate errors such as
        # ConnectionResetError > ConnectionError:
        # https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/#retry-on-failure
        # See new API imports in this post:
        # https://stackoverflow.com/questions/15431044/can-i-set-max-retries-for-requests-request
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("https://", adapter)
        http.mount("http://", adapter)
        response = http.get(api_url, headers=headers)
        data = response.json()
        return data
