import * as pulumi from '@pulumi/pulumi'
import * as azure from '@pulumi/azure'
import * as automation from '@pulumi/pulumi/automation'
import * as dotenv from 'dotenv'
import handler from './handler'

dotenv.config({ path: './../.env' })

const geteventGridResources = async () => {
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

  const storageAccount = new azure.storage.Account('eventgridsa', {
    resourceGroupName: resourceGroup.name,
    location: resourceGroup.location,
    accountReplicationType: 'LRS',
    accountTier: 'Standard',
    accountKind: 'StorageV2'
  })

  const container = new azure.storage.Container('container', {
    storageAccountName: storageAccount.name,
    containerAccessType: 'private'
  })

  const eventGridEvent = azure.eventgrid.events.onGridBlobCreated(
    'eventGridTrigger',
    {
      storageAccount,
      appSettings: {
        APPINSIGHTS_INSTRUMENTATIONKEY: insights.instrumentationKey
      },
      callback: handler
    }
  )

  return {
    eventGridStorageAccountName: storageAccount.name,
    eventGridStorageContainerName: container.name,
    functionApp: eventGridEvent.functionApp.endpoint.apply(e =>
      e.replace('/api/', '')
    )
  }
}

module.exports = geteventGridResources().then(e => e)
