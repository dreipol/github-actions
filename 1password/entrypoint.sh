#!/bin/sh

set -e

eval $(echo -n $ONE_PASS_MASTER_PASSWORD | op signin $ONE_PASS_SUBDOMAIN.1password.com ${ONE_PASS_EMAIL} $ONE_PASS_SECRET_KEY)

for var in "$@"
do
    echo "get secret for $var"
    password_value=$(op get item $var | jq -r ".details.password")
    echo ::set-env name=${var}::${password_value}
done