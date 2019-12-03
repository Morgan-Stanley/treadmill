#!/bin/bash

SCRIPTDIR=$(cd $(dirname $0) && pwd)

mkdir -p ~/.provision

function run {
    checksum=~/.provision/$(basename $1)
    if $(md5sum -c --status $checksum); then
        echo $1 is up to date.
    else
        $1
        if [ $? -ne 0 ]; then
                echo "$1 failed."
                exit 1
        fi
        md5sum $1 > $checksum
    fi
}

run $SCRIPTDIR/install-base.sh
run $SCRIPTDIR/install-ipa-packages.sh
run $SCRIPTDIR/venv.sh
run $SCRIPTDIR/configure-etc-hosts.sh
run $SCRIPTDIR/configure-profile_ipa.sh
run $SCRIPTDIR/install-ipa-server.sh

echo 'IPA provisioned!'
