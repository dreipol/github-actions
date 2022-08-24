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

date=$(date +%Y-%m-%d -d "30 days ago")
image_tags=$(gcloud container images list-tags --filter="timestamp.datetime < '${date}'" --format='get(tags)' $GCR_IMAGE)
for value in $image_tags
do
    num_tags=$(echo $value | sed 's/[^;]//g' | awk '{ print length }')
    if [ "$num_tags" -lt "1" ]
	then
        echo "DELETE $value"
	      gcloud container images delete-tag --quiet $GCR_IMAGE:$value
    fi
done
