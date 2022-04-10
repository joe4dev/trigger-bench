#!/usr/bin/env bash

# Helper to maintain code duplication.
# SHOULD: Find a valid Typescript config such that
# the shared code can reside in a shared directory.
# Currently, importing dependencies that are only
# available in the subdirectories (e.g., in queue)
# but not at this higher shared level causes
# the deployment to fail.

cp http/handler.ts queue/handler.ts
cp http/handler.ts database/runtimes/node/CosmosTrigger/index.ts
cp http/handler.ts storage/handler.ts
cp http/handler.ts serviceBus/handler.ts
cp http/handler.ts eventGrid/handler.ts
cp http/handler.ts eventHub/handler.ts
cp http/handler.ts timer/handler.ts
