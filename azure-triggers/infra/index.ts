// Pulumi infrastructure imports
import * as pulumi from '@pulumi/pulumi'
import * as azure from '@pulumi/azure'
import * as automation from '@pulumi/pulumi/automation'

// Runtime dependencies
import * as Identity from '@azure/identity'
import * as Storage from '@azure/storage-blob'
import * as cosmos from '@azure/cosmos'
import * as StorageQueue from '@azure/storage-queue'
import * as EventHub from '@azure/event-hubs'
import * as serviceBus from '@azure/service-bus'
import * as appInsights from 'applicationinsights'
import axios from 'axios'
import * as dotenv from 'dotenv'

dotenv.config({ path: './../.env' })

const supportedTriggers = [
  'http',
  'storage',
  'queue',
  'database',
  'timer',
  'eventHub',
  'eventGrid',
  'serviceBus',
]

type Response = {
  status: number
  headers: {}
  body: string
}

const getHttpFunction = (url: string,operationId: any) =>
  new Promise<Response>(resolve => {
    axios
      .get(url + "?operationId=" + operationId)
      .then(() =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain',
            'operationId' : operationId
          },
          body: 'AZURE - HTTP trigger successfully started'
        })
      )
      .catch(e =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - HTTP trigger benchmark failed to start\n\nError: ${e.message}`
        })
      )
  })

const getStorageFunction = (
  container: any,
  storageAccount: any,
  operationId: any
) =>
  new Promise<Response>(resolve => {
    let credential = new Identity.EnvironmentCredential()

    const blobServiceClient = new Storage.BlobServiceClient(
      `https://${storageAccount}.blob.core.windows.net`,
      credential
    )

    const containerClient = blobServiceClient.getContainerClient(container)
    const content: string = 'Hello world!'
    const blobName = `${new Date().getTime()}.txt`
    const blockBlobClient = containerClient.getBlockBlobClient(blobName)

    blockBlobClient
      .upload(content, content.length, {
        metadata: {
          operationId
        }
      })
      .then(() =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: 'AZURE - Storage trigger benchmark successfully started'
        })
      )
      .catch(e =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - Storage trigger benchmark failed to start\n\nError: ${e.message}`
        })
      )
  })

const getQueueFunction = (queue: any, storageAccount: any, operationId: any) =>
  new Promise<Response>(resolve => {
    let credential = new Identity.EnvironmentCredential()

    const queueServiceClient = new StorageQueue.QueueServiceClient(
      `https://${storageAccount}.queue.core.windows.net`,
      credential
    )

    const queueClient = queueServiceClient.getQueueClient(queue)

    const base64Encode = (str: string) => Buffer.from(str).toString('base64')

    // Send message (operationId) to queue
    queueClient
      .sendMessage(base64Encode(operationId))
      .then(() =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: 'AZURE - Queue trigger benchmark successfully started'
        })
      )
      .catch(e =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - Queue trigger benchmark failed to start\n\nError: ${e.message} \n Queue: ${queue}`
        })
      )
  })

const getDatabaseFunction = (
  databaseName: string,
  containerName: string,
  operationId: any
) =>
  new Promise<Response>(async resolve => {
    const endpoint = process.env.ACCOUNTDB_ENDPOINT!
    const key = process.env.ACCOUNTDB_PRIMARYKEY!
    const client = new cosmos.CosmosClient(
      `AccountEndpoint=${endpoint};AccountKey=${key};`
    )
    const container = client.database(databaseName).container(containerName)

    console.log('Insert item to database')

    const newItem = {
      newOperationId: operationId,
      isComplete: false
    }

    await container.items
      .create(newItem)
      .then(() =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - Database trigger benchmark successfully started`
        })
      )
      .catch((e: any) =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - Database trigger benchmark failed to start\n\nError: ${e.message}`
        })
      )
  })

const getTimerFunction = (url: string, operationId: any) =>
  new Promise<Response>(resolve => {
    axios
      .post(
        url,
        { input: operationId },
        {
          headers: {
            'x-functions-key': process.env['AZURE_TIMER_MASTERKEY']!,
            'Content-type': 'application/json'
          }
        }
      )
      .then(() =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: 'AZURE - Timer trigger successfully started'
        })
      )
      .catch(e =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - Timer trigger failed to start\n\nError: ${e.message}`
        })
      )
  })

const getServiceBusResources = (serviceBusName: string, topicName: string, operationId: string) =>
  new Promise<Response>(async resolve => {

    let credential = new Identity.EnvironmentCredential()

    const client = new serviceBus.ServiceBusClient(
      `${serviceBusName}.servicebus.windows.net`,
      credential
    )

    const messages = [{ body: operationId }]

    const sender = client.createSender(topicName)

    try {
      // Tries to send all messages in a single batch.
      // Will fail if the messages cannot fit in a batch.
      // await sender.sendMessages(messages);

      // create a batch object
      let batch = await sender.createMessageBatch()
      for (let i = 0; i < messages.length; i++) {
        // for each message in the arry

        // try to add the message to the batch
        if (!batch.tryAddMessage(messages[i])) {
          // if it fails to add the message to the current batch
          // send the current batch as it is full
          await sender.sendMessages(batch)

          // then, create a new batch
          batch = await sender.createMessageBatch()

          // now, add the message failed to be added to the previous batch to this batch
          if (!batch.tryAddMessage(messages[i])) {
            // if it still can't be added to the batch, the message is probably too big to fit in a batch
            throw new Error('Message too big to fit in a batch')
          }
        }
      }

      // Send the last created batch of messages to the topic
      await sender
        .sendMessages(batch)
        .then(() =>
          resolve({
            status: 200,
            headers: {
              'content-type': 'text/plain'
            },
            body: 'AZURE - Service Bus trigger successfully started'
          })
        )
        .catch(e =>
          resolve({
            status: 200,
            headers: {
              'content-type': 'text/plain'
            },
            body: `AZURE - Service Bus trigger failed to start\n\nError: ${e.message}`
          })
        )

      console.log(`Sent a batch of messages to the topic: ${topicName}`)

      // Close the sender
      await sender.close()
    } finally {
      await client.close()
    }
  })

const getEventHubFunction = (
  eventHubName: string,
  eventHubNamespace: string,
  operationId: string
) =>
  new Promise<Response>(async resolve => {
    const producer = new EventHub.EventHubProducerClient(
      eventHubNamespace + '.servicebus.windows.net',
      eventHubName,
      new Identity.EnvironmentCredential()
    )

    const batch = await producer.createBatch()

    batch.tryAdd({ body: operationId })

    producer
      .sendBatch(batch)
      .then(async () => {
        await producer.close()
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: 'AZURE - Event Hub trigger benchmark successfully started'
        })
      })
      .catch(async e => {
        await producer.close()
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - Event Hub trigger benchmark failed to start\n\nError in sending batch: ${e.message} \n`
        })
      })
  })

const getEventGridFunction = (
  storageAccountName: string,
  storageContainerName: string,
  operationId: any
) =>
  new Promise<Response>(async resolve => {
    let credential = new Identity.EnvironmentCredential()

    const blobServiceClient = new Storage.BlobServiceClient(
      `https://${storageAccountName}.blob.core.windows.net`,
      credential
    )

    const containerClient = blobServiceClient.getContainerClient(
      storageContainerName
    )
    const content: string = 'Hello world!'
    const blobName = operationId
    const blockBlobClient = containerClient.getBlockBlobClient(blobName)

    blockBlobClient
      .upload(content, content.length, {
        metadata: {
          operationId
        }
      })
      .then(() =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: 'AZURE - Event Grid trigger successfully started'
        })
      )
      .catch(e =>
        resolve({
          status: 200,
          headers: {
            'content-type': 'text/plain'
          },
          body: `AZURE - Event Grid trigger failed to start\n\nError: ${e.message}`
        })
      )
  })

const handler = async (context: any, req: any) => {
  // Setup application insights
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
    .setDistributedTracingMode(appInsights.DistributedTracingModes.AI_AND_W3C)
  appInsights.defaultClient.setAutoPopulateAzureProperties(true)
  appInsights.start()

  // Get URL params
  const triggerType: string = req.query && req.query.trigger
  const validTrigger: string | boolean =
    triggerType && (supportedTriggers.includes(triggerType))
  const triggerInput: string = req.query && req.query.input

  if (validTrigger && triggerInput) {
    // Start an AI Correlation Context using the provided Function context
    const correlationContext: any = appInsights.startOperation(context, req)

    if (triggerType === 'http') {
      // HTTP trigger
      return appInsights.wrapWithCorrelationContext(async () => {
        const startTime = Date.now()

        const response = await getHttpFunction(triggerInput,correlationContext.operation.id)

        // Track dependency on completion
        appInsights.defaultClient.trackDependency({
          name: 'http_trigger',
          dependencyTypeName: triggerType,
          resultCode: response.status,
          success: true,
          duration: Date.now() - startTime,
          id: correlationContext.operation.parentId,
          data: ''
        })
        appInsights.defaultClient.flush()

        return response
      }, correlationContext)()
    }

    if (triggerType === 'queue') {
      const queueInputs = triggerInput.split(',')
      // Queue trigger
      return appInsights.wrapWithCorrelationContext(async () => {
        const startTime = Date.now()

        const response = await getQueueFunction(
          queueInputs[0],
          queueInputs[1],
          correlationContext.operation.id
        )

        // Track dependency on completion
        appInsights.defaultClient.trackDependency({
          name: 'queue_trigger',
          dependencyTypeName: triggerType,
          resultCode: response.status,
          success: true,
          duration: Date.now() - startTime,
          id: correlationContext.operation.parentId,
          data: ''
        })
        appInsights.defaultClient.flush()
        return response
      }, correlationContext)()
    }
    if (triggerType === 'storage') {
      const storageInputs = triggerInput.split(',')
      // Storage trigger
      if (storageInputs.length === 2) {
        return appInsights.wrapWithCorrelationContext(async () => {
          const startTime = Date.now()

          const response = await getStorageFunction(
            storageInputs[0],
            storageInputs[1],
            correlationContext.operation.parentId
          )

          // Track dependency on completion
          appInsights.defaultClient.trackDependency({
            name: 'storage_trigger',
            dependencyTypeName: triggerType,
            resultCode: response.status,
            success: true,
            duration: Date.now() - startTime,
            id: correlationContext.operation.parentId,
            data: ''
          })
          appInsights.defaultClient.flush()
          return response
        }, correlationContext)()
      }
    }
    // Database (SQL) trigger
    if (triggerType === 'database') {
      const databaseInputs = triggerInput.split(',')
      //console.log('Database trigger started')
      if (databaseInputs.length === 2) {
        return appInsights.wrapWithCorrelationContext(async () => {
          const startTime = Date.now()

          const response = await getDatabaseFunction(
            databaseInputs[0],
            databaseInputs[1],
            correlationContext.operation.id
          )

          // Track dependency on completion
          appInsights.defaultClient.trackDependency({
            name: 'database_trigger',
            dependencyTypeName: triggerType,
            resultCode: response.status,
            success: true,
            duration: Date.now() - startTime,
            id: correlationContext.operation.parentId,
            data: ''
          })
          appInsights.defaultClient.flush()
          return response
        }, correlationContext)()
      }
    }

    if (triggerType == 'timer') {
      return appInsights.wrapWithCorrelationContext(async () => {
        const startTime = Date.now()

        const response = await getTimerFunction(
          triggerInput,
          correlationContext.operation.parentId
        )

        // Track dependency on completion
        appInsights.defaultClient.trackDependency({
          name: 'timer_trigger',
          dependencyTypeName: triggerType,
          resultCode: response.status,
          success: true,
          duration: Date.now() - startTime,
          id: correlationContext.operation.parentId,
          data: ''
        })
        appInsights.defaultClient.flush()
        return response
      }, correlationContext)()
    }
    if (triggerType === 'serviceBus') {
      const serviceBusInputs = triggerInput.split(',')
      return appInsights.wrapWithCorrelationContext(async () => {
        const startTime = Date.now()

        const response = await getServiceBusResources(
          serviceBusInputs[0],
          serviceBusInputs[1],
          correlationContext.operation.parentId
        )

        // Track dependency on completion
        appInsights.defaultClient.trackDependency({
          name: 'serviceBus_trigger',
          dependencyTypeName: triggerType,
          resultCode: response.status,
          success: true,
          duration: Date.now() - startTime,
          id: correlationContext.operation.parentId,
          data: req.query.input
        })
        appInsights.defaultClient.flush()

        return response
      }, correlationContext)()
    }

    if (triggerType == 'eventHub') {
      const eventHubInputs = triggerInput.split(',')
      return appInsights.wrapWithCorrelationContext(async () => {
        const startTime = Date.now()

        const response = await getEventHubFunction(
          eventHubInputs[0],
          eventHubInputs[1],
          correlationContext.operation.id
        )

        // Track dependency on completion
        appInsights.defaultClient.trackDependency({
          name: 'eventHub_trigger',
          dependencyTypeName: triggerType,
          resultCode: response.status,
          success: true,
          duration: Date.now() - startTime,
          id: correlationContext.operation.parentId,
          data: ''
        });

        appInsights.defaultClient.flush()
        return response
      }, correlationContext)()
    }

    if (triggerType == 'eventGrid') {
      const eventGridInputs = triggerInput.split(',')
      return appInsights.wrapWithCorrelationContext(async () => {
        const startTime = Date.now()

        const response = await getEventGridFunction(
          eventGridInputs[0],
          eventGridInputs[1],
          correlationContext.operation.id
        )

        // Track dependency on completion
        appInsights.defaultClient.trackDependency({
          name: 'eventGrid_trigger',
          dependencyTypeName: triggerType,
          resultCode: response.status,
          success: true,
          duration: Date.now() - startTime,
          id: correlationContext.operation.parentId,
          data: ''
        })
        appInsights.defaultClient.flush()
        return response
      }, correlationContext)()
    }
  }

  // If either parameter is missing or is invalid
  return {
    status: 400,  // 400 bad request
    headers: {
      'content-type': 'text/plain'
    },
    body: JSON.stringify(req)
  }
}

const getEndpoint = async () => {
  const user = await automation.LocalWorkspace.create({}).then(ws =>
    ws.whoAmI().then(i => i.user)
  )
  const shared = new pulumi.StackReference(
    `${user}/${process.env.PULUMI_PROJECT_NAME}/shared`
  )

  const resourceGroupId = shared.requireOutput('resourceGroupId')
  const resourceGroup = azure.core.ResourceGroup.get(
    'ResourceGroup',
    resourceGroupId
  )
  const insightsId = shared.requireOutput('insightsId')
  const insights = azure.appinsights.Insights.get('Insights', insightsId)

  // Infrastructure endpoint (HTTP trigger)
  return new azure.appservice.HttpEventSubscription('InfraEndpoint', {
    resourceGroup,
    location: process.env.PULUMI_AZURE_LOCATION,
    callback: handler,
    appSettings: {
      APPINSIGHTS_INSTRUMENTATIONKEY: insights.instrumentationKey,
      AZURE_CLIENT_ID: process.env.AZURE_CLIENT_ID,
      AZURE_TENANT_ID: process.env.AZURE_TENANT_ID,
      AZURE_CLIENT_SECRET: process.env.AZURE_CLIENT_SECRET,
      ACCOUNTDB_ENDPOINT: process.env.ACCOUNTDB_ENDPOINT,
      ACCOUNTDB_PRIMARYKEY: process.env.ACCOUNTDB_PRIMARYKEY,
      AZURE_TIMER_MASTERKEY: process.env.AZURE_TIMER_MASTERKEY
    }
  })
}

exports.url = getEndpoint().then(endpoint => endpoint.url)
