FROM google/cloud-sdk:280.0.0-alpine
RUN apk add --no-cache --update coreutils
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]