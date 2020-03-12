FROM dreipol/alpine-curl
RUN apk add --no-cache --update jq
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]