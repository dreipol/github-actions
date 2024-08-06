#!/bin/sh

set -e

if [ -n "${WORKING_DIRECTORY}" ]; then
  cd $WORKING_DIRECTORY
fi

docker buildx create --driver docker-container --use --name BUILDX_BUILDER
docker buildx build \
    -t $GCR_IMAGE:$GITHUB_SHA \
    --output type=docker \
    --build-arg PROJECT_NAME=$PROJECT_NAME \
    --build-arg GIT_REV=$GCR_IMAGE:$GITHUB_SHA \
    --build-arg GITHUB_SHA=$GITHUB_SHA \
    --build-arg GITHUB_REF_SLUG=$GITHUB_REF_SLUG \
    ${DOCKER_BUILD_OPTS} \
    .
