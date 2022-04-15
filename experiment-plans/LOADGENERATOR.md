# Loadgenerator Specifications

The vantage point for each cloud provider is setup as documented under [LOADGENERATOR.md](../serverless-benchmarker/docs/LOADGENERATOR.md).
The following specifications were used.

## Requirements

* Decent CPU such that the load generator does not become a bottleneck (using 4 cores)
* Decent network connectivity for load generation
* Enough storage for performance logs (depends on experiment)

## AWS

* Region: `us-east-1`
* Instance Type: `t3.xlarge`
  * Price: `$0.166400 per hour`
  * Specs: https://instances.vantage.sh/?selected=t3.large,t3.xlarge

## Azure

* Region: `eastus`
* Instance Type: `B4ms`
  * Price: `$0.166 per hour`
  * Specs: https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/#pricing
