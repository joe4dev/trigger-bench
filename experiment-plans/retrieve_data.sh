#!/usr/bin/env bash

# Shell script using rsync to copy a dataset from a remote load generator (lg).
# Supported configuration via environment variables:
# * SB_USER: user name of the Linux user (default ubuntu)
# * SB_DATA_SOURCE: host alias (configured in ~/.ssh/config), IP address, or DNS name of host with data (default lg_aws)
# * SB_DATA_DIR: local path where data should be stored (default ../data/${DATA_SOURCE})

# Parent directory of this script. Source: https://stackoverflow.com/a/246128
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

USER="${SB_USER:-ubuntu}"
DATA_SOURCE="${SB_DATA_SOURCE:-lg_aws}"
DEFAULT_DATA_DIR="${SCRIPT_DIR}/../data/${DATA_SOURCE}"

SRC="${USER}@${DATA_SOURCE}:/home/${USER}/"
DEST="${SB_DATA_DIR:-"$DEFAULT_DATA_DIR"}"

# Copy all sb "logs" directories but nothing else (i.e., ignore other repo content or logs)
# Optionally preview using: --dry-run
rsync -amhvzP --stats --exclude='sb-env' --exclude='.vscode-server' --exclude='.serverless' --exclude='.git' --exclude='node_modules' --include='logs/*/*' --include='*/' --exclude='*' "$SRC" "$DEST"
