#!/bin/sh

set -e

GITHUB_CHECK_SUITE_ID=$(curl -s https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID} | jq -r '.check_suite_id')
echo "::set-env name=GITHUB_CHECK_SUITE_ID::${GITHUB_CHECK_SUITE_ID}"
