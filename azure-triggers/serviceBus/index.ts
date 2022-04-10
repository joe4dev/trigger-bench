import * as pulumi from '@pulumi/pulumi'
import * as azure from '@pulumi/azure'
import * as automation from '@pulumi/pulumi/automation'
import handler from './handler'
import * as dotenv from 'dotenv'

dotenv.config({ path: './../.env' })

const getServiceBusResources = async () => {
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

  const serviceBusNamespace = new azure.servicebus.Namespace(
    'serviceBusNamespace',
    {
      location: resourceGroup.location,
      resourceGroupName: resourceGroup.name,
      sku: 'standard',
      tags: {
        source: 'example'
      }
    }
  )

  const topic = new azure.servicebus.Topic('serviceBusTopic', {
    namespaceId: serviceBusNamespace.id,
    enablePartitioning: true
  })

  const subscription2 = topic.onEvent('serviceBusTrigger', {
    location: process.env.PULUMI_AZURE_LOCATION,
    callback: handler,
    appSettings: {
      APPINSIGHTS_INSTRUMENTATIONKEY: insights.instrumentationKey
    }
  })

  return {
    serviceBusNamespace: serviceBusNamespace.name,
    topicName: topic.name,
    functionApp: subscription2.functionApp.endpoint.apply(e =>
      e.replace('/api/', '')
    )
  }
}

module.exports = getServiceBusResources().then(e => e)
