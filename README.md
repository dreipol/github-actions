# github-actions

Repository with github actions for the CI workflow

## build
```
dreipol/github-actions/build@master
```
Builds a docker image with the commit sha as tag.
If an image with the same tag already exists in the registry, it will use that image instead of building
another one. Tries to use the docker cache from master, stage, branch to speed up the build.

Required env variables:
* GCP_SERVICEACCOUNT_KEY
* GCR_IMAGE
* GITHUB_REF_SLUG
* GITHUB_SHA   
* PROJECT_NAME


## deploy
```
dreipol/github-actions/deploy@master
```
Pulls an image with the commit hash from the registry and pushes it to the openshift cluster.

Required env variables:
* ASPECTRA_REGISTRY
* ASPECTRA_TAG
* DEPLOY_IMAGE
* GCP_SERVICEACCOUNT_KEY
* GCR_IMAGE
* GITHUB_SHA   
* OPENSHIFT_TOKEN
* OPENSHIFT_USER


## push
```
dreipol/github-actions/push@master
```
Pushes an image with the commit sha as tag to the google registry. 
Also tags it with the current branch name.

Required env variables:
* GCP_SERVICEACCOUNT_KEY
* GCR_IMAGE
* GITHUB_REF_SLUG
* GITHUB_SHA   

## slack
```
dreipol/github-actions/slack@master
```
Sends a slack notification that a build has started.

Required env variables:
* ENVIRONMENT
* GITHUB_REPOSITORY
* GITHUB_RUN_ID
* SLACK_WEBHOOK

## slugify
```
dreipol/github-actions/slugify@master
```
Creates slug names for branches so that we can use them as docker tags

Required env variables:
* GITHUB_HEAD_REF
* GITHUB_BASE_REF
* GITHUB_REF
* GITHUB_SHA