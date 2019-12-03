#!/bin/bash

SCRIPTDIR=$(cd $(dirname $0) && pwd)

mkdir -p ~/.provision

function run {
    checksum=~/.provision/$(basename $1)
    md5sum -c $checksum
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
run $SCRIPTDIR/configure-etc-hosts.sh
run $SCRIPTDIR/install-ipa-client.sh
run $SCRIPTDIR/create-users.sh
run $SCRIPTDIR/install-node-packages.sh
run $SCRIPTDIR/venv.sh
run $SCRIPTDIR/configure-profile_ipa.sh
run $SCRIPTDIR/install-node-components_ipa.sh

echo 'treadmill node provisioned!'
