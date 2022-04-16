TRIGGER_TYPE=''
RUNTIME=''
FILE_NAME='../.env'
FUNCTION_URL=''
LOCATION=''
FUNCTION_APP_URL=''
FUNCTIONAPP_NAME=''

deploy_shared_resources() {
  echo "PULUMI_AZURE_LOCATION=\"$LOCATION\"" >>'./.env'
  echo "RUNTIME=\"$RUNTIME\"" >>'./.env'
  
  cd shared/ && pulumi stack select shared -c && pulumi up -f -y

  echo "PULUMI_AZURE_LOCATION=\"$LOCATION\"" >>$FILE_NAME
  echo "RUNTIME=\"$RUNTIME\"" >>$FILE_NAME

  # Get App Id
  APP_ID=$(pulumi stack output insightsAppId)
  # Get Insights name
  INSIGHTS_NAME=$(pulumi stack output insightsName)
  # Get Resource group name
  RESOURCE_GROUP=$(pulumi stack output resourceGroupName)
  # Get Function app name
  FUNCTION_APP_URL=$(pulumi stack output functionAppUrl)
  FUNCTIONAPP_NAME=$(pulumi stack output functionAppName)

  # Create API key to be able to use Azure Insights REST API TODO use it with REST API
  az config set extension.use_dynamic_install=yes_without_prompt # Required to install and use app-insights module

  # Navigate back to parent directory
  cd ..
}

deploy_http_trigger() {
  deploy_shared_resources

  # Deploy HTTP trigger
  cd http/ && pulumi stack select trigger -c && pulumi up -f -y

  # Get url to HTTP trigger gateway
  TRIGGER_URL=$(pulumi stack output url)
  FUNCTION_APP=$(pulumi stack output functionApp)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=http&input=$TRIGGER_URL\"" >>$FILE_NAME
  # Initialize receiver polling of function app. Henrik's explanation:
  # The reason for saving FUNCTION_APP_URL and then curl it was that we had some issues on instability
  # in when receivers starts to polling (for some triggers) for data. That's why we are calling the
  # receiver base API URL to awake it up.
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP}
  echo "Start HTTP trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=http&input=$TRIGGER_URL"
}

deploy_storage_trigger() {
  # Deploy shared resources
  deploy_shared_resources

  # Deploy storage trigger
  cd storage/ && pulumi stack select trigger -c && pulumi up -f -y

  # Assign required roles, get storage account name and container name
  STORAGE_ACCOUNT_NAME=$(pulumi stack output storageAccountName)
  CONTAINER_NAME=$(pulumi stack output containerName)
  FUNCTION_APP=$(pulumi stack output functionApp)
  ##
  # assign role "Storage Blob Data Contributor" to relevant asignees
  ##

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=storage&input=$CONTAINER_NAME,$STORAGE_ACCOUNT_NAME\"" >>$FILE_NAME
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP}
  echo "Start storage trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=storage&input=$CONTAINER_NAME,$STORAGE_ACCOUNT_NAME"
}

deploy_queue_trigger() {
  # Deploy shared resources
  deploy_shared_resources

  # Deploy queue trigger
  cd queue/ && pulumi stack select trigger -c && pulumi up -f -y

  # Get storage account name and queue name
  STORAGE_ACCOUNT_NAME=$(pulumi stack output storageAccountName)
  QUEUE_NAME=$(pulumi stack output queueName)
  FUNCTION_APP=$(pulumi stack output functionApp)

  ##
  # assign role "Storage Blob Data Contributor" to relevant asignees
  ##

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=queue&input=$QUEUE_NAME,$STORAGE_ACCOUNT_NAME\"" >>$FILE_NAME
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP}
  echo "Start queue trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=queue&input=$QUEUE_NAME,$STORAGE_ACCOUNT_NAME"
}

deploy_database_trigger() {
  # Deploy shared resources
  deploy_shared_resources

  # Deploy database trigger
  cd database/ && pulumi stack select trigger -c && pulumi up -f -y

  # Get storage account name and database name
  CONTAINER_NAME=$(pulumi stack output containerName)
  DATABASE_NAME=$(pulumi stack output databaseName)

  cd runtimes/node
  
  func azure functionapp publish $FUNCTIONAPP_NAME --$RUNTIME --force

  cd ..
  cd ..
  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=database&input=$DATABASE_NAME,$CONTAINER_NAME\"" >>$FILE_NAME
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP_URL}
  echo "Start database trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=database&input=$DATABASE_NAME,$CONTAINER_NAME"
}

deploy_timer_trigger() {
  # Deploy shared resources
  deploy_shared_resources

  # Deploy database trigger
  cd timer/ && pulumi stack select trigger -c && pulumi up -f -y

  # Get timer function app name and trigger name
  TIMER_FUNCTION_APP_NAME=$(pulumi stack output timerFunctionAppName)
  TIMER_TRIGGER_NAME=$(pulumi stack output timerTriggerAppName)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=timer&input=https://$TIMER_FUNCTION_APP_NAME/admin/functions/$TIMER_TRIGGER_NAME\"" >>$FILE_NAME
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP_URL}
  echo "$BENCHMARK_URL?trigger=timer&input=https://$TIMER_FUNCTION_APP_NAME/admin/functions/$TIMER_TRIGGER_NAME"
}

deploy_serviceBus_trigger() {
  # Deploy shared resources
  deploy_shared_resources

  # Deploy serviceBus trigger
  cd serviceBus/ && pulumi stack select trigger -c && pulumi up -f -y

  # Get storage account name and serviceBus name
  SERVICE_BUS_NAMESPACE=$(pulumi stack output serviceBusNamespace)
  TOPIC_NAME=$(pulumi stack output topicName)
  FUNCTION_APP=$(pulumi stack output functionApp)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=serviceBus&input=$SERVICE_BUS_NAMESPACE,$TOPIC_NAME\"" >>$FILE_NAME
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP}
  echo "Start serviceBus trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=serviceBus&input=$SERVICE_BUS_NAMESPACE,$TOPIC_NAME"
}

deploy_eventHub_trigger() {
  # Deploy shared resources
  deploy_shared_resources

  # Deploy database trigger
  cd eventHub/ && pulumi stack select trigger -c && pulumi up -f -y

  # Get timer function app name and trigger name
  EVENT_HUB_NAME=$(pulumi stack output eventHubName)
  EVENT_HUB_NAMESPACE=$(pulumi stack output eventHubNamespace)
  FUNCTION_APP=$(pulumi stack output functionApp)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=eventHub&input=$EVENT_HUB_NAME,$EVENT_HUB_NAMESPACE\"" >>$FILE_NAME
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP}
  echo "Start event hub trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=eventHub&input=$EVENT_HUB_NAME,$EVENT_HUB_NAMESPACE"
}

deploy_eventGrid_trigger() {
  # Deploy shared resources
  deploy_shared_resources

  # Deploy event grid trigger
  cd eventGrid/ && pulumi stack select trigger -c && pulumi up -f -y

  # Get timer function app name and trigger name
  EVENT_GRID_STORAGE_NAME=$(pulumi stack output eventGridStorageAccountName)
  EVENT_GRID_CONTAINER_NAME=$(pulumi stack output eventGridStorageContainerName)
  FUNCTION_APP=$(pulumi stack output functionApp)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select infra -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Write URL to .env"
  echo "BENCHMARK_URL=\"$BENCHMARK_URL?trigger=eventGrid&input=$EVENT_GRID_STORAGE_NAME,$EVENT_GRID_CONTAINER_NAME\"" >>$FILE_NAME
  echo "Initilize Function App"
  curl -s -o /dev/null -w "http_code=%{http_code}\n" ${FUNCTION_APP}
  echo "Start event grid trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=eventGrid&input=$EVENT_GRID_STORAGE_NAME,$EVENT_GRID_CONTAINER_NAME"
}

# Read input flags
while getopts 't:r:l:' flag; do
  case "${flag}" in
  t) TRIGGER_TYPE="${OPTARG}" ;;
  r) RUNTIME="${OPTARG}" ;;
  l) LOCATION="${OPTARG}" ;;
  *) exit 1 ;;
  esac
done

if [ "$RUNTIME" = 'node' ] || [ "$RUNTIME" = 'dotnet' ]; then
  echo 'Runtime valid'
elif [ "$RUNTIME" = '' ]; then
  echo 'Default runtime: node'
  RUNTIME='node'
else
  echo 'ERROR: Unsupported runtime'
  exit
fi

if [ "$LOCATION" = 'northeurope' ] || [ "$LOCATION" = 'eastus' ]; then
  echo 'Location valid'
elif ["$LOCATION" = '']; then
  echo 'Default Location: northeurope'
  LOCATION='northeurope'
else
  echo 'ERROR: Unsupported location'
  exit
fi

# Decide which trigger to deploy based on input flag
if [ "$TRIGGER_TYPE" = 'http' ]; then
  deploy_http_trigger
elif [ "$TRIGGER_TYPE" = 'storage' ]; then
  deploy_storage_trigger
elif [ "$TRIGGER_TYPE" = 'queue' ]; then
  deploy_queue_trigger
elif [ "$TRIGGER_TYPE" = 'database' ]; then
  deploy_database_trigger
elif [ "$TRIGGER_TYPE" = 'timer' ]; then
  deploy_timer_trigger
elif [ "$TRIGGER_TYPE" = 'serviceBus' ]; then
  deploy_serviceBus_trigger
elif [ "$TRIGGER_TYPE" = 'eventHub' ]; then
  deploy_eventHub_trigger
elif [ "$TRIGGER_TYPE" = 'eventGrid' ]; then
  deploy_eventGrid_trigger
else
  echo 'Error: Unsupported trigger'
fi
