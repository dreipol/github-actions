#!/bin/sh

set -e

oc login "${OPENSHIFT_HOST}" --token="${OPENSHIFT_TOKEN}"
echo "Wait 5 Seconds to check rollout progress"
sleep 5

# One line per DeploymentConfig: "<name> <image1> <image2> ..."
# Uses oc's built-in jsonpath because origin-cli >= 4.16 no longer ships jq.
DC_IMAGES=$(oc -n "${OPENSHIFT_PROJECT}" get dc \
  -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[*].image}{"\n"}{end}')

DEPLOYMENT_CONFIGS=$(printf '%s\n' "${DC_IMAGES}" | grep '/reverse-proxy@' | cut -d' ' -f1)

if [ -z "${DEPLOYMENT_CONFIGS}" ]; then
    echo "No DeploymentConfigs using a /reverse-proxy@ image found in ${OPENSHIFT_PROJECT}"
    exit 0
fi

for value in ${DEPLOYMENT_CONFIGS}
do
    oc -n "${OPENSHIFT_PROJECT}" rollout status "dc/${value}"
done
