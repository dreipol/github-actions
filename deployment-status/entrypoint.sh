#!/bin/sh

set -e

oc login ${OPENSHIFT_HOST} --token=${OPENSHIFT_TOKEN}
oc -n ${OPENSHIFT_PROJECT} rollout status dc/${DEPLOYMENT_CONFIG}