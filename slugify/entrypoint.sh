#!/bin/sh -l

slug_ref() {
    echo "$1" \
         | tr "[:upper:]" "[:lower:]" \
         | sed -r 's#refs/[^\/]*/##;s/[~\^]+//g;s/[^a-zA-Z0-9]+/-/g;s/^-+\|-+$//g;s/^-*//;s/-*$//' \
         | cut -c1-63
}

short_sha(){
  echo "$1" \
        | cut -c1-8
}

echo "GITHUB_REF_SLUG=$(slug_ref $GITHUB_REF)" >> $GITHUB_ENV
echo "GITHUB_HEAD_REF_SLUG=$(slug_ref $GITHUB_HEAD_REF)" >> $GITHUB_ENV
echo "GITHUB_BASE_REF_SLUG=$(slug_ref $GITHUB_BASE_REF)" >> $GITHUB_ENV
echo "GITHUB_SHA_SHORT=$(short_sha $GITHUB_SHA)" >> $GITHUB_ENV
