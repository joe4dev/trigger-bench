# Burst sizes
burst_sizes = [10, 50, 100, 300]
inter_burst_time_seconds = 10
num_target_samples = 3000

def k6_options(burst_size):
    """Returns a k6 workload config for a given burst size.
    * k6 advanced scenarios with startTime: https://k6.io/docs/using-k6/scenarios/advanced-examples/
    * k6 iteration executor: https://k6.io/docs/using-k6/scenarios/executors/per-vu-iterations/
    """
    num_bursts = round(num_target_samples / burst_size)
    options = {
        "scenarios":{
            f"burst_{burst+1} ": {
                "executor": "per-vu-iterations",
                "vus": burst_size,
                "iterations": 1,
                "startTime": f"{inter_burst_time_seconds*burst}s",
            } for burst in range(num_bursts)
        }
    }
    return options


for burst_size in burst_sizes:
    print(burst_size)
    print(k6_options(burst_size))
