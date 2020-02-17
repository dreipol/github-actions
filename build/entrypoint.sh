#!/bin/sh

set -e

echo $HOME
ls -la $HOME/.docker
ls -la /github/home/.docker

if ! docker pull $GCR_IMAGE:$GITHUB_SHA;
then
  echo $GCR_IMAGE:$GITHUB_REF_SLUG $GCR_IMAGE:master $GCR_IMAGE:stage | xargs -P10 -n1 docker pull || true && \
  docker build \
      --cache-from=$GCR_IMAGE:master \
      --cache-from=$GCR_IMAGE:stage \
      --cache-from=$GCR_IMAGE:$GITHUB_REF_SLUG \
      --build-arg PROJECT_NAME=$PROJECT_NAME \
      -t $GCR_IMAGE:$GITHUB_SHA .
fi
