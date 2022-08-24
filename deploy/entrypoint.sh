#!/bin/sh

set -e

CONFIG_DIRECTORY="deployment-config/${DEPLOY_ENVIRONMENT}"
if test -d "$CONFIG_DIRECTORY"; then
  echo "Kustomize config found. Applying it to openshift..."
  oc login --server=${OPENSHIFT_HOST} --token=${OPENSHIFT_TOKEN}
  oc apply -k $CONFIG_DIRECTORY
else
  echo "Could not find kustomize configuration in ${CONFIG_DIRECTORY}"
fi
