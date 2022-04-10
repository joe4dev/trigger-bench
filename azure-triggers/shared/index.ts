import * as azure from '@pulumi/azure'
import * as azuread from '@pulumi/azuread'
import * as pulumi from '@pulumi/pulumi'
import * as cosmosdb from '@pulumi/azure/cosmosdb'
import * as fs from 'fs'
import * as dotenv from 'dotenv'
import { FunctionApp } from './functionApp'

dotenv.config({ path: './../.env' })

const runtime = process.env.RUNTIME!

const resourceGroup = new azure.core.ResourceGroup('ResourceGroup', {
  location: process.env.PULUMI_AZURE_LOCATION!
})

const insights = new azure.appinsights.Insights('Insights', {
  location: resourceGroup.location,
  resourceGroupName: resourceGroup.name,
  applicationType: 'other'
})

const readTelemetry = new azure.appinsights.ApiKey('readTelemetry', {
  applicationInsightsId: insights.id,
  readPermissions: ['aggregate', 'api', 'draft', 'extendqueries', 'search']
})

const current = azuread.getClientConfig({})
const application = new azuread.Application('application', {
  displayName: 'azure-trigger-bench',
  owners: [current.then((current: { objectId: any }) => current.objectId)]
})

const servicePrincipal = new azuread.ServicePrincipal('servicePrincipal', {
  applicationId: application.applicationId,
  appRoleAssignmentRequired: false,
  owners: [current.then((current: { objectId: any }) => current.objectId)]
})

const clientSecret = new azuread.ApplicationPassword('exampleClientSecret', {
  applicationObjectId: application.objectId,
  displayName: 'azure-trigger-bench-secret',
  endDateRelative: '3600h'
})

let sqlAccount = new cosmosdb.Account('databaseTrigger', {
  resourceGroupName: resourceGroup.name,
  offerType: 'Standard',
  consistencyPolicy: {
    consistencyLevel: 'Session'
  },
  geoLocations: [{ location: resourceGroup.location, failoverPriority: 0 }],
  enableFreeTier: true
})

const sqlDatabase = new cosmosdb.SqlDatabase('sqlDatabase', {
  accountName: sqlAccount.name,
  resourceGroupName: resourceGroup.name
})

const sqlContainer = new cosmosdb.SqlContainer('sqlContainer', {
  databaseName: sqlDatabase.name,
  accountName: sqlAccount.name,
  resourceGroupName: resourceGroup.name,
  partitionKeyPath: '/newOperationId'
})

const resourceGroupArgs = {
  resourceGroupName: resourceGroup.name,
  location: resourceGroup.location
}

const storageAccount = new azure.storage.Account(`${runtime}sa`, {
  ...resourceGroupArgs,

  accountKind: 'StorageV2',
  accountTier: 'Standard',
  accountReplicationType: 'LRS'
})

const runAsPackageContainer = new azure.storage.Container(`${runtime}-c`, {
  storageAccountName: storageAccount.name,
  containerAccessType: 'private'
})

const connectionString = pulumi.interpolate`AccountEndpoint=${sqlAccount.endpoint};AccountKey=${sqlAccount.primaryKey};`

// New version of Henrik+Henrik uses runtime as function name.
// The current analysis depends on the function names of the previous version
// to detect different trigger types.
// SHOULD: Implement more generic trigger detection in generic handler to get rid of this dependency on function name.
var endpoint = new FunctionApp(`${runtime}`, {
  resourceGroup: resourceGroup,
  storageAccount: storageAccount,
  appInsights: insights,
  storageContainer: runAsPackageContainer,
  //path: 'azuretrigger/httpcs/bin/publish',
  version: '~4',
  runtime: runtime,
  appSettings: {
    DATABASE_NAME: sqlDatabase.name,
    CONTAINER_NAME: sqlContainer.name,
    APPLICATIONINSIGHTS_CONNECTION_STRING: insights.connectionString,
    ACCOUNTDB_ENDPOINT: sqlAccount.endpoint,
    ACCOUNTDB_KEY: sqlAccount.primaryKey,
    DATABASE_CONNECTION_STRING: connectionString
  }
})

new azure.authorization.Assignment('storageBlobDataContributor', {
  scope: resourceGroup.id,
  roleDefinitionName: 'Storage Blob Data Contributor',
  principalId: servicePrincipal.objectId
})

new azure.authorization.Assignment('storageQueueDataContributor', {
  scope: resourceGroup.id,
  roleDefinitionName: 'Storage Queue Data Contributor',
  principalId: servicePrincipal.objectId
})

new azure.authorization.Assignment('eventHubDataOwner', {
  scope: resourceGroup.id,
  roleDefinitionName: 'Azure Event Hubs Data Owner',
  principalId: servicePrincipal.objectId
})

new azure.authorization.Assignment('timerOwner', {
  scope: resourceGroup.id,
  roleDefinitionName: 'Owner',
  principalId: servicePrincipal.objectId
})

new azure.authorization.Assignment('serviceBusOwner', {
  scope: resourceGroup.id,
  roleDefinitionName: 'Azure Service Bus Data Owner',
  principalId: servicePrincipal.objectId
})

writeEnv()

// Export ids and names of resources to import them in other projects
exports.resourceGroupId = resourceGroup.id
exports.resourceGroupName = resourceGroup.name
exports.insightsId = insights.id
exports.insightsName = insights.name
exports.insightsAppId = insights.appId // Required by Azure Insights REST API
exports.functionAppName = endpoint.functionAppName
exports.functionAppUrl = endpoint.url

function writeEnv () {
  if (fs.existsSync('../.env')) {
    fs.unlinkSync('../.env')
  }

  sqlAccount.name.apply(name =>
    fs.writeFile(
      '../.env',
      'ACCOUNTDB_NAME="' + name + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Cosmos DB name not added')
          throw err
        }
        console.log('Cosmos DB name - Added')
      }
    )
  )

  sqlAccount.id.apply(id =>
    fs.writeFile(
      '../.env',
      'ACCOUNTDB_ID="' + id + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Cosmos DB ID not added')
          throw err
        }
        console.log('Cosmos DB ID - Added')
      }
    )
  )

  sqlAccount.name.apply(name =>
    fs.writeFile(
      '../.env',
      'ACCOUNTDB_ENDPOINT="https://' + name + '.documents.azure.com:443/"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Cosmos DB account endpoint not added')
          throw err
        }
        console.log('Cosmos DB account endpoint - Added')
      }
    )
  )

  sqlAccount.primaryKey.apply(key =>
    fs.writeFile(
      '../.env',
      'ACCOUNTDB_PRIMARYKEY="' + key + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Cosmos DB primary key not added')
          throw err
        }
        console.log('Cosmos DB primary key - Added')
      }
    )
  )

  sqlDatabase.name.apply(name =>
    fs.writeFile(
      '../.env',
      'DATABASE_NAME="' + name + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Database name not added')
          throw err
        }
        console.log('Database name - Added')
      }
    )
  )

  sqlDatabase.id.apply(id =>
    fs.writeFile(
      '../.env',
      'DATABASE_ID="' + id + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Database id not added')
          throw err
        }
        console.log('Database id - Added')
      }
    )
  )

  sqlContainer.name.apply(name =>
    fs.writeFile(
      '../.env',
      'CONTAINER_NAME="' + name + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Container name not added')
          throw err
        }
        console.log('Container name - Added')
      }
    )
  )

  sqlContainer.id.apply(id =>
    fs.writeFile(
      '../.env',
      'CONTAINER_ID="' + id + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Cosmos DB primary key not added')
          throw err
        }
        console.log('Cosmos DB primary key - Added')
      }
    )
  )

  servicePrincipal.applicationTenantId.apply(applicationTenantId =>
    fs.writeFile(
      '../.env',
      'AZURE_TENANT_ID="' + applicationTenantId + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Tenant ID not added')
          throw err
        }
        console.log('Tenant ID - Added')
      }
    )
  )

  servicePrincipal.objectId.apply(objectId =>
    fs.writeFile(
      '../.env',
      'AZURE_PRINCIPAL_ID="' + objectId + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Principal ID not added')
          throw err
        }
        console.log('Tenant ID - Added')
      }
    )
  )

  application.applicationId.apply(id =>
    fs.writeFile(
      '../.env',
      'AZURE_CLIENT_ID="' + id + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Client ID not added')
          throw err
        }
        console.log('Client ID - Added')
      }
    )
  )

  clientSecret.value.apply(value =>
    fs.writeFile(
      '../.env',
      'AZURE_CLIENT_SECRET="' + value + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Client Secret not added')
          throw err
        }
        console.log('Client Secret - Added')
      }
    )
  )

  application.objectId.apply(objectId =>
    fs.writeFile(
      '../.env',
      'AZURE_OBJECT_ID="' + objectId + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Object ID not added')
          throw err
        }
        console.log('Object ID - Added')
      }
    )
  )

  readTelemetry.apiKey.apply(key =>
    fs.writeFile(
      '../.env',
      'INSIGHTS_API_KEY="' + key + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: API_KEY not added')
          throw err
        }
        console.log('API_KEY - Added')
      }
    )
  )

  insights.appId.apply(id =>
    fs.writeFile(
      '../.env',
      'INSIGHTS_APP_ID="' + id + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: APP ID not added')
          throw err
        }
        console.log('APP ID - Added')
      }
    )
  )

  insights.connectionString.apply(cs =>
    fs.writeFile(
      '../.env',
      'INSIGHTS_CONNECTION_STRING="' + cs + '"\n',
      { flag: 'a' },
      (err: any) => {
        if (err) {
          console.log('ERROR: Insight connection string not added')
          throw err
        }
        console.log('Insight connection string - Added')
      }
    )
  )

  fs.writeFile(
    '../.env',
    'PULUMI_PROJECT_NAME="azure-trigger-bench" \n',
    { flag: 'a' },
    (err: any) => {
      if (err) {
        console.log('ERROR: PULUMI variables not added')
        throw err
      }
      console.log('PULUMI variables - Added')
    }
  )
}
