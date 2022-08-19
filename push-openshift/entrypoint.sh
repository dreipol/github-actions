#!/bin/sh

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

if [ -n "${OPENSHIFT_TOKEN}" ]; then
  echo "Logging into openshift cluster with OPENSHIFT_TOKEN..."
  echo ${OPENSHIFT_TOKEN} | docker login -u ${OPENSHIFT_USER} --password-stdin ${ASPECTRA_REGISTRY}
else
  echo "OPENSHIFT_TOKEN was empty, not performing auth" 1>&2
fi

docker pull $GCR_IMAGE:$GITHUB_SHA
docker tag $GCR_IMAGE:$GITHUB_SHA $DEPLOY_IMAGE:$ASPECTRA_TAG
docker push $DEPLOY_IMAGE:$ASPECTRA_TAG
