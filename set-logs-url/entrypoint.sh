#!/bin/sh

set -e


JOB_ID=$(curl  -L -H "Authorization: Bearer ${GITHUB_TOKEN}" https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs | jq ".jobs[] | select(.name == \"${JOB_NAME}\") | .id")
LOGS_URL="https://github.com/${GITHUB_REPOSITORY}/commit/${GITHUB_SHA}/checks/${JOB_ID}/logs"
echo "::set-env name=DREIPOL_JOB_ID::${JOB_ID}"
echo "::set-env name=DREIPOL_LOGS_URL::${LOGS_URL}"
