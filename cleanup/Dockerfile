FROM google/cloud-sdk:508.0.0-stable
RUN apk add --no-cache --update coreutils
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]