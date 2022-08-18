#!/bin/sh

set -e

if [ -n "${GCP_SERVICEACCOUNT_KEY}" ]; then
  echo "Logging into gcr.io with GCLOUD_SERVICE_ACCOUNT_KEY..."
  echo ${GCP_SERVICEACCOUNT_KEY} | base64 -d > /tmp/key.json
  gcloud auth activate-service-account --quiet --key-file /tmp/key.json
  gcloud auth configure-docker --quiet
else
  echo "GCLOUD_SERVICE_ACCOUNT_KEY was empty, not performing auth" 1>&2
fi

if ! docker pull $GCR_IMAGE:$GITHUB_SHA;
then
  docker buildx create --driver docker-container --use --name BUILDX_BUILDER
  docker buildx build \
      -t $GCR_IMAGE:$GITHUB_SHA \
      --output type=image,push=true \
      --build-arg PROJECT_NAME=$PROJECT_NAME \
      --build-arg GIT_REV=$GCR_IMAGE:$GITHUB_SHA \
      --build-arg GITHUB_REF_SLUG=$GITHUB_REF_SLUG \
      --cache-to=type=registry,ref=${GCR_IMAGE}:cache-${CI_COMMIT_REF_SLUG},mode=max \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-master \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-main \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-develop \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-${CI_COMMIT_REF_SLUG} \
      ${DOCKER_BUILD_OPTS}
      .
fi
