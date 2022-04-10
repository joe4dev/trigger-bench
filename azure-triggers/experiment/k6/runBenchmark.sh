TRIGGER_TYPE=''

deploy_http_benchmark() {
  echo "Deploying http trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t http
  cd experiment/k6
  echo "Http trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting Http benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Http benchmark finished"
}

deploy_storage_benchmark() {
  echo "Deploying storage trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t storage
  cd experiment/k6
  echo "Storage trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting storage benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Storage benchmark finished"
}

deploy_queue_benchmark() {
  echo "Deploying queue trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t queue
  cd experiment/k6
  echo "Queue trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting queue benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Queue benchmark finished"
}

deploy_database_benchmark() {
  echo "Deploying database trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t database
  cd experiment/k6
  echo "Database trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting database benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Database benchmark finished"
}

deploy_timer_benchmark() {
  echo "Deploying timer trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t timer
  cd experiment/k6
  echo "Timer trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting timer benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Timer benchmark finished"
}

deploy_serviceBus_benchmark() {
  echo "Deploying Service bus trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t serviceBus
  cd experiment/k6
  echo "Service bus trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting Service bus benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Service bus benchmark finished"
}

deploy_eventHub_benchmark() {
  echo "Deploying Event hub trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t eventHub
  cd experiment/k6
  echo "Event hub trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting Event hub benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Event hub benchmark finished"
}

deploy_eventGrid_benchmark() {
  echo "Deploying Event grid trigger"
  cd ..
  cd ..
  bash ./deploy.sh -t eventGrid
  cd experiment/k6
  echo "Event grid trigger deployed"
  echo "Wait 10s before starting benchmark"
  sleep 10
  echo "Starting Event grid benchmark"
  k6 run -e BENCHMARK_URL=$(grep BENCHMARK_URL ./../../.env | cut -d '"' -f2) benchmark.js
  echo "Event grid benchmark finished"
}

deploy_all_benchmarks() {
  deploy_http_benchmark
  deploy_storage_benchmark
  deploy_queue_benchmark
  deploy_database_benchmark
  deploy_timer_benchmark
  deploy_serviceBus_benchmark
  deploy_eventHub_benchmark
  deploy_eventGrid_benchmark
}

# Read input flags
while getopts 't:' flag; do
  case "${flag}" in
  t) TRIGGER_TYPE="${OPTARG}" ;;
  *) exit 1 ;;
  esac
done

# Decide which trigger to deploy based on input flag
if [ "$TRIGGER_TYPE" = 'http' ]; then
  deploy_http_benchmark
elif [ "$TRIGGER_TYPE" = 'storage' ]; then
  deploy_storage_benchmark
elif [ "$TRIGGER_TYPE" = 'queue' ]; then
  deploy_queue_benchmark
elif [ "$TRIGGER_TYPE" = 'database' ]; then
  deploy_database_benchmark
elif [ "$TRIGGER_TYPE" = 'timer' ]; then
  deploy_timer_benchmark
elif [ "$TRIGGER_TYPE" = 'serviceBus' ]; then
  deploy_serviceBus_benchmark
elif [ "$TRIGGER_TYPE" = 'eventHub' ]; then
  deploy_eventHub_benchmark
elif [ "$TRIGGER_TYPE" = 'eventGrid' ]; then
  deploy_eventGrid_benchmark
elif [ "$TRIGGER_TYPE" = 'all' ]; then
  deploy_all_benchmarks
else
  echo 'Error: Unsupported trigger'
fi