import * as pulumi from '@pulumi/pulumi'
import * as azure from '@pulumi/azure'
import * as automation from '@pulumi/pulumi/automation'
import * as dotenv from 'dotenv'
import handler from './handler'

dotenv.config({ path: './../.env' })

const getStorageResources = async () => {
  // Import shared resources
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

  const storageAccount = new azure.storage.Account('account', {
    resourceGroupName: resourceGroup.name,
    location: resourceGroup.location,
    accountTier: 'Standard',
    accountKind: 'StorageV2',
    accountReplicationType: 'LRS'
  })

  const queue = new azure.storage.Queue('queue', {
    storageAccountName: storageAccount.name
  })

  // Queue trigger
  const queueEvent = queue.onEvent('queueTrigger', {
    resourceGroup,
    location: process.env.PULUMI_AZURE_LOCATION,
    callback: handler,
    hostSettings: {
      extensions: {
        queues: {
          maxPollingInterval: '00:00:01', // 1s
          batchSize: 32,
          newBatchThreshold: 16,
          visibilityTimeout: '0',
          maxDequeueCount: 5
        }
      }
    },
    appSettings: {
      APPINSIGHTS_INSTRUMENTATIONKEY: insights.instrumentationKey,
      AZURE_CLIENT_ID: process.env.AZURE_CLIENT_ID,
      AZURE_TENANT_ID: process.env.AZURE_TENANT_ID,
      AZURE_CLIENT_SECRET: process.env.AZURE_CLIENT_SECRET
    }
  })

  return {
    storageAccountName: storageAccount.name,
    queueName: queue.name,
    functionApp: queueEvent.functionApp.endpoint.apply(e =>
      e.replace('/api/', '')
    )
  }
}

module.exports = getStorageResources().then(e => e)
