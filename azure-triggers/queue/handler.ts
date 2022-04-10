import * as appInsights from 'applicationinsights'

// NOTE: Run clone_handler.sh after modifying this file.
// It is currently copied into each trigger directory because
// sharing the same file in a directory above breaks deployment.
// SHOULD: Fix typescript config to share code instead of copy!

// Application Insights in Azure Function:
// https://github.com/microsoft/ApplicationInsights-node.js#azure-functions

// There will always be the `receiver0` span to capture
// the first line of code and add trace annotations for certain event sources.
const numReceiverSpans = 5

// Function handler for different trigger types.
const handler = async (context: any, event: any) => {
    // const firstLOCTime = Date.now()
    // Setup Azure Application Insights:
    // https://github.com/microsoft/ApplicationInsights-node.js#configuration
    appInsights
        .setup()
        .setAutoDependencyCorrelation(true)
        .setAutoCollectRequests(true)
        .setAutoCollectPerformance(true, true)
        .setAutoCollectExceptions(true)
        .setAutoCollectDependencies(true)
        .setAutoCollectConsole(true)
        .setUseDiskRetryCaching(false)
        .setSendLiveMetrics(false)
        .setUseDiskRetryCaching(false)
        .setDistributedTracingMode(appInsights.DistributedTracingModes.AI_AND_W3C)
    appInsights.defaultClient.setAutoPopulateAzureProperties(true)
    appInsights.start()
    // const instrumentationInitializationTime = Date.now()

    // Start an AI Correlation Context using the provided Function context
    const correlationContext: any = appInsights.startOperation(
        context,
        'correlationContextOperation'
    )

    // Parse root trace id from incoming event. Parsing depends on trigger type.
    let rootTraceId = ''
    // Azure Triggers and Bindings: https://docs.microsoft.com/en-us/azure/azure-functions/functions-triggers-bindings
    // Example for HTTP trigger: https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-http-webhook-trigger
    const triggerType = context['bindingDefinitions'].find((e: any) => e.direction === 'in').type
    if (triggerType === 'httpTrigger') {
        // Auto-correlation supported for http trigger,
        // therefore, the correlation context should have the
        // correct operation id equal to the root trace id.
        // rootTraceId = correlationContext.operation.id
        rootTraceId = event['query']['operationId']
    } else if (triggerType === 'cosmosDBTrigger') {
        rootTraceId = event[0]['newOperationId']
    } else if (triggerType === 'queueTrigger') {
        rootTraceId = event
    } else if (triggerType === 'eventGridTrigger') {
        rootTraceId = context["bindings"]["message"]["subject"].split('/').pop()
    } else if (triggerType === 'eventHubTrigger') {
        rootTraceId = event
    } else if (triggerType === 'serviceBusTrigger') {
        rootTraceId = event.replace("|","").split(".")[0]
    } else if (triggerType === 'blobTrigger') {
        rootTraceId = context["bindingData"]["metadata"]["operationId"].replace('|', '').split('.')[0]
    } else if (triggerType === 'timerTrigger') {
        rootTraceId = context["bindingData"]["timer"].replace("|","").split(".")[0]
    } else {
        console.error('Could not detect rootTraceId for this trigger.')
    }

    // TODO: Remove debug logging
    console.log(`context=${JSON.stringify(context)}`)
    console.log(`event=${JSON.stringify(event)}`)
    console.log(`correlationContext=${JSON.stringify(correlationContext)}`)
    console.log(`process.version=${process.version}`)

    // Wrap the Function runtime with correlationContext
    // This automatically populates the operationId for tracking code
    // Notice the trailing `()` after the invocation of wrapWithCorrelationContext
    return appInsights.wrapWithCorrelationContext(async () => {
        const startTime = Date.now() // Start trackRequest timer

        // Idle operation
        const response = {
            status: 200,
            headers: {
                'content-type': 'text/plain',
            },
            body: `Hello World!`,
        }
        // Track first timestamp in function
        appInsights.defaultClient.trackDependency({
            name: 'receiver0',
            dependencyTypeName: 'CUSTOM',
            resultCode: response.status,
            success: true,
            duration: Date.now() - startTime,
            // Parent id will be automatically populated in operation_ParentId
            // id: correlationContext.operation.parentId,
            // Description: Remote call data.
            // This is the most detailed information about the call, such as full URL or SQL statement.
            data: rootTraceId
        })

        // Add additional receiver subsegments to measure Insights timestamp overhead
        for (let i = 1; i <= numReceiverSpans; i++) {
            const extraStartTime = Date.now()

            // Intentionally idle.

            appInsights.defaultClient.trackDependency({
                name: `receiver${i}`,
                dependencyTypeName: 'CUSTOM',
                resultCode: response.status,
                success: true,
                duration: Date.now() - extraStartTime,
                data: ''
            })
        }

        // Inspect node runtime version
        appInsights.defaultClient.trackTrace({
            message: 'Node version',
            properties: {
                node_version: process.version,
            }
        })

        // Immediately send all queued telemetry data
        appInsights.defaultClient.flush()
        return response
    }, correlationContext)()
}

export default handler
