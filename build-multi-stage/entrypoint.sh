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

if [ -n "${WORKING_DIRECTORY}" ]; then
  cd $WORKING_DIRECTORY
fi


if ! docker pull $GCR_IMAGE:$GITHUB_SHA;
then
  docker buildx create --driver docker-container --use --name BUILDX_BUILDER

  docker buildx build \
      -t $GCR_IMAGE:$GITHUB_SHA-frontend \
      --output type=docker \
      --build-arg PROJECT_NAME=$PROJECT_NAME \
      --build-arg GIT_REV=$GCR_IMAGE:$GITHUB_SHA \
      --build-arg GITHUB_SHA=$GITHUB_SHA \
      --build-arg GITHUB_REF_SLUG=$GITHUB_REF_SLUG \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-frontend-master \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-frontend-main \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-frontend-develop \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-frontend-${GITHUB_REF_SLUG} \
      --cache-to=type=registry,ref=${GCR_IMAGE}:cache-frontend-${GITHUB_REF_SLUG},mode=max \
      --target=frontend \
      ${DOCKER_BUILD_OPTS} \
      .

  docker buildx build \
      -t $GCR_IMAGE:$GITHUB_SHA \
      --output type=docker \
      --build-arg PROJECT_NAME=$PROJECT_NAME \
      --build-arg GIT_REV=$GCR_IMAGE:$GITHUB_SHA \
      --build-arg GITHUB_SHA=$GITHUB_SHA \
      --build-arg GITHUB_REF_SLUG=$GITHUB_REF_SLUG \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-backend-master \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-backend-main \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-backend-develop \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-backend-${GITHUB_REF_SLUG} \
      --cache-to=type=registry,ref=${GCR_IMAGE}:cache-backend-${GITHUB_REF_SLUG},mode=max \
      --target=backend \
      ${DOCKER_BUILD_OPTS} \
      .
fi