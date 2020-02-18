#!/bin/bash

set -e

curl -X POST --data-urlencode "payload={ \"text\": \"Build for $PROJECT_NAME-$ENVIRONMENT started. <https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}| Check the progress on github>\", }" $SLACK_WEBHOOK