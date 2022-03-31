TRIGGER_TYPE=''

deploy_http_trigger() {
  # Deploy shared resources
  cd shared/ && pulumi stack select dev -c && pulumi up -f -y

  cd ..

  # Deploy HTTP trigger
  cd http/ && pulumi stack select dev -c && pulumi up -f -y

  # Get url to HTTP trigger gateway
  TRIGGER_URL=$(pulumi stack output url)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select dev -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Start HTTP trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=http&input=$TRIGGER_URL"
}

deploy_storage_trigger() {
  # Deploy shared resources
  cd shared/ && pulumi stack select dev -c && pulumi up -f -y

  cd ..

  # Deploy storage trigger
  cd storage/ && pulumi stack select dev -c && pulumi up -f -y

  # Get ID of the bucket
  BUCKET_ID=$(pulumi stack output bucketId)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select dev -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Start storage trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=storage&input=$BUCKET_ID"
}

deploy_queue_trigger() {
  # Deploy shared resources
  cd shared/ && pulumi stack select dev -c && pulumi up -f -y

  cd ..

  # Deploy queue trigger
  cd queue/ && pulumi stack select dev -c && pulumi up -f -y

  # Get url of the queue
  QUEUE_URL=$(pulumi stack output queueUrl)

  cd ..

  # Deploy infrastructure
  cd infra/ && pulumi stack select dev -c && pulumi up -f -y

  # Get url to benchmark gateway
  BENCHMARK_URL=$(pulumi stack output url)

  echo "Start queue trigger benchmark:"
  echo "$BENCHMARK_URL?trigger=queue&input=$QUEUE_URL"
}

# Read input flags
while getopts 't:' flag; do
  case "${flag}" in
    t) TRIGGER_TYPE="${OPTARG}" ;;
    *) exit 1 ;;
  esac
done

# Decide which trigger to deploy based on input flag
if [ "$TRIGGER_TYPE" = 'http' ]
then
  deploy_http_trigger
elif [ "$TRIGGER_TYPE" = 'storage' ]
then
  deploy_storage_trigger
elif [ "$TRIGGER_TYPE" = 'queue' ]
then
  deploy_queue_trigger
else
  echo 'Error: Unsupported trigger'
fi