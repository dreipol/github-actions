echo "::set-env name=BRANCH_NAME::${GITHUB_REF#refs/heads/}"
echo "::set-env name=GIT_COMMIT_SHA::${GITHUB_SHA}"