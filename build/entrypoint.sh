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

if [ -n "${CUSTOM_CACHE_TAG}" ]; then
    # This is a "Custom Cache Tag Buster": The current setup only allows "code-based" SHA-Tagged Docker builds.
    # In case of Static Site Generation, the SHA can be "stale". We need to bust it in order to re-generate.
    IMAGE_TAG="${CUSTOM_CACHE_TAG}"
    echo "Using CUSTOM_CACHE_TAG: $IMAGE_TAG"
else
    IMAGE_TAG="$GITHUB_SHA"
    echo "Using GITHUB_SHA: $IMAGE_TAG"
fi


if ! docker pull $GCR_IMAGE:$IMAGE_TAG;
then
  docker buildx create --driver docker-container --use --name BUILDX_BUILDER
  docker buildx build \
      -t $GCR_IMAGE:$IMAGE_TAG \
      --output type=docker \
      --build-arg PROJECT_NAME=$PROJECT_NAME \
      --build-arg GIT_REV=$GCR_IMAGE:$GITHUB_SHA \
      --build-arg GITHUB_SHA=$GITHUB_SHA \
      --build-arg GITHUB_REF_SLUG=$GITHUB_REF_SLUG \
      --cache-to=type=registry,ref=${GCR_IMAGE}:cache-${GITHUB_REF_SLUG},mode=max \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-master \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-main \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-develop \
      --cache-from=type=registry,ref=${GCR_IMAGE}:cache-${GITHUB_REF_SLUG} \
      ${DOCKER_BUILD_OPTS} \
      .
fi
