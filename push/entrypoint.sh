#!/bin/bash

set -e

if [ -n "${GCP_SERVICEACCOUNT_KEY}" ]; then
  echo "Logging into gcr.io with GCLOUD_SERVICE_ACCOUNT_KEY..."
  echo ${GCP_SERVICEACCOUNT_KEY} | base64 -d > /tmp/key.json
  gcloud auth activate-service-account --quiet --key-file /tmp/key.json
  gcloud auth configure-docker --quiet
  gcloud auth configure-docker eu-west6-docker.pkg.dev --quiet
else
  echo "GCLOUD_SERVICE_ACCOUNT_KEY was empty, not performing auth" 1>&2
fi

docker tag $GCR_IMAGE:$GITHUB_SHA $GCR_IMAGE:$GITHUB_REF_SLUG
docker push $GCR_IMAGE:$GITHUB_SHA
docker push $GCR_IMAGE:$GITHUB_REF_SLUG