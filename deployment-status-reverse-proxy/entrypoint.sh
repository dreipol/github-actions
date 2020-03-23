#!/bin/sh

set -e

oc login ${OPENSHIFT_HOST} --token=${OPENSHIFT_TOKEN}
echo "Wait 5 Seconds to check rollout progress"
sleep 5
DEPLOYMENT_CONFIGS=$(oc get dc -o json | jq -r '.items[] | select(.spec.template.spec.containers[]? | .image | try contains("/reverse-proxy@")) | "\(.metadata.name)"')

for value in $DEPLOYMENT_CONFIGS
do
    oc -n ${OPENSHIFT_PROJECT} rollout status dc/${value}
done


