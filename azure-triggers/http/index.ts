import * as pulumi from '@pulumi/pulumi'
import * as azure from '@pulumi/azure'
import * as automation from '@pulumi/pulumi/automation'
import * as dotenv from 'dotenv'
import handler from './handler'

dotenv.config({ path: './../.env' })

const getEndpoint = async () => {

  const user = await automation.LocalWorkspace.create({})
    .then((ws) => ws.whoAmI()
      .then((i) => i.user));
  const shared = new pulumi.StackReference(`${user}/${process.env.PULUMI_PROJECT_NAME}/shared`);

  const resourceGroupId = shared.requireOutput('resourceGroupId');
  const resourceGroup = azure.core.ResourceGroup.get('ResourceGroup', resourceGroupId);
  const insightsId = shared.requireOutput('insightsId');
  const insights = azure.appinsights.Insights.get('Insights', insightsId);

  // HTTP trigger
  const httpEvent = new azure.appservice.HttpEventSubscription('httpTrigger', {
    resourceGroup,
    location: process.env.PULUMI_AZURE_LOCATION,
    callback: handler,
    appSettings: {
      APPINSIGHTS_INSTRUMENTATIONKEY: insights.instrumentationKey,
    },
  });

  return {
    url: httpEvent.url,
    functionApp: httpEvent.functionApp.endpoint.apply(e => e.replace("/api/",""))
  }
};

module.exports = getEndpoint().then(e => e)
