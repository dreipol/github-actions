#!/bin/sh

set -e

DEFAULT_TEXT="Build for ${GITHUB_REPOSITORY} ${ENVIRONMENT} started. <https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}| Check the progress on github>"

TEXT=${TEXT:=$DEFAULT_TEXT}
TEXT=$(echo $TEXT | envsubst)

echo $TEXT