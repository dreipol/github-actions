FROM quay.io/openshift/origin-cli:4.12 as oc

FROM google/cloud-sdk:280.0.0-alpine
COPY --from=oc /usr/bin/oc /usr/bin/oc
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]