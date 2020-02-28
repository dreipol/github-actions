#!/bin/sh

set -e

oc login ${OPENSHIFT_HOST} --token=${OPENSHIFT_TOKEN}
echo "Wait 5 Seconds to check rollout progress"
sleep 5
oc -n ${OPENSHIFT_PROJECT} rollout status dc/${DEPLOYMENT_CONFIG}