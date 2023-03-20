FROM alpine/curl
RUN apk add --no-cache --update gettext curl jq bash

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]