FROM curlimages/curl:7.88.1
RUN apk add --no-cache --update gettext
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
