ARG PULUMI_VERSION=3.28.0
FROM pulumi/pulumi:${PULUMI_VERSION}

# Install Azure Functions Core Tools used for database trigger deployment
# https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
    && sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/debian/$(lsb_release -rs | cut -d'.' -f 1)/prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list' \
    && apt-get update \
    && apt-get install azure-functions-core-tools-4

# NOTE: There is an official image containing core-tools but that's currently huge in size ~2.67GB:
# See size issue: https://github.com/Azure/azure-functions-docker/issues/323
# AZURE_FUNC_IMAGE = 'mcr.microsoft.com/azure-functions/node:3.0-node12-core-tools'
