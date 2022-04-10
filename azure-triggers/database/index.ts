import * as cosmosdb from '@pulumi/azure/cosmosdb'
import * as dotenv from 'dotenv'

dotenv.config({ path: './../.env' })

// CODE WILL LATER BE REFACTORED AND THIS FILE WILL NOT BE NECESSARY ANYMORE
const getDatabaseResources = async () => {
  const sqlDatabase = cosmosdb.SqlDatabase.get(
    process.env.DATABASE_NAME!,
    process.env.DATABASE_ID!
  )

  const sqlContainer = cosmosdb.SqlContainer.get(
    process.env.CONTAINER_NAME!,
    process.env.CONTAINER_ID!
  )

  return {
    databaseName: sqlDatabase.name,
    containerName: sqlContainer.name
  }
}

module.exports = getDatabaseResources().then(e => e)
