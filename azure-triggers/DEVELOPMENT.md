# Development

Checkout the [SB Development Docs](../serverless-benchmarker/docs/DEVELOPMENT.md) for helpful tips such as interactive debugging through ipdb `import ipdb; ipdb.set_trace()`.

## Manual Setup

These instructions describe how to install the dependencies locally.

1. [Install Pulumi](https://www.pulumi.com/docs/get-started/aws/begin/#install-pulumi)
2. [Configure Azure credentials](https://www.pulumi.com/docs/get-started/azure/begin/#configure-pulumi-to-access-your-microsoft-azure-account)
3. [Install Node.js](https://nodejs.org/en/download/)
4. [Install the Azure Functions Core Tools (func)](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools)

## Generic Handler

All trigger types share the same handler generic implementation.
The authoritative version is located in the http trigger [http/handler.ts](./http/handler.ts) and can be automatically replicated through `clone_handler.sh`.
This workaround is a limitation of the current Typescript configuration because deployment fails to deploy if the handler tries to import dependencies unavailable in node_modules of a shared directory (e.g., azure-triggers/handlers/handler.ts).

## Database Trigger

The CosmosDB database trigger requires a custom configuration (see [function.json](./database/runtimes/node/CosmosTrigger/function.json)) to trigger a function for each change rather than aggregating multiple changes:

* `maxItemsPerInvocation=1`
* `checkpointDocumentCount=1`

Further, we customize the delay in milliseconds in between polling a partition for new changes on the feed as follows:

* `feedPollDelay=1` (default is 5000ms)

Some of these configuration options are not available in the Pulumi Azure Classic provider (e.g., see [PR in Pulumi](https://github.com/pulumi/pulumi-azure/pull/1052)) and therefore we implemented a workaround (see [Henrik's fix](https://github.com/henriklagergren/azure-triggers-study/commit/b8a14980636c4584a1dbd98d584f6a3f3eae46fa)) using the Azure Function Tools (func) to deploy the function app.

Related resources:

* [List of Azure CosmosDB properties](https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-cosmosdb-v2-trigger?tabs=in-process%2Cfunctionsv2&pivots=programming-language-javascript#configuration)
* [Azure recommendations to improve trigger time](https://docs.microsoft.com/en-us/azure/cosmos-db/sql/troubleshoot-changefeed-functions#my-changes-take-too-long-to-be-received)
* [Pulumi Azure Classic supported Typescript mixins](https://github.com/pulumi/pulumi-azure/blob/master/sdk/nodejs/cosmosdb/zMixins.ts)
