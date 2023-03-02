FROM dreipol/alpine-curl
RUN apk add --no-cache --update gettext
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
