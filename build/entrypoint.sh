#!/bin/sh

set -e

if [ -n "${GCP_SERVICEACCOUNT_KEY}" ]; then
  echo "Logging into gcr.io with GCLOUD_SERVICE_ACCOUNT_KEY..."
  echo ${GCP_SERVICEACCOUNT_KEY} | base64 -d > /tmp/key.json
  gcloud auth activate-service-account --quiet --key-file /tmp/key.json
  gcloud auth configure-docker --quiet
  gcloud auth configure-docker europe-west6-docker.pkg.dev --quiet
else
  echo "GCLOUD_SERVICE_ACCOUNT_KEY was empty, not performing auth" 1>&2
fi

if ! docker pull $GCR_IMAGE:$GITHUB_SHA;
then
  echo $GCR_IMAGE:$GITHUB_REF_SLUG $GCR_IMAGE:master $GCR_IMAGE:stage | xargs -P10 -n1 docker pull || true && \
  docker build \
      --cache-from=$GCR_IMAGE:$GITHUB_REF_SLUG \
      --cache-from=$GCR_IMAGE:stage \
      --cache-from=$GCR_IMAGE:master \
      --build-arg PROJECT_NAME=$PROJECT_NAME \
      --build-arg GIT_REV=$GCR_IMAGE:$GITHUB_SHA \
      --build-arg GITHUB_SHA=$GITHUB_SHA \
      --build-arg GITHUB_REF_SLUG=$GITHUB_REF_SLUG \
      -t $GCR_IMAGE:$GITHUB_SHA .
fi
