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
run $SCRIPTDIR/install-master-packages.sh
run $SCRIPTDIR/install-ldap.sh
run $SCRIPTDIR/create-users.sh
run $SCRIPTDIR/venv.sh
run $SCRIPTDIR/configure-etc-hosts.sh
run $SCRIPTDIR/configure-profile.sh
run $SCRIPTDIR/install-tinydns.sh
run $SCRIPTDIR/install-master-components.sh

echo 'master provisioned!'
