#!/bin/sh

SCRIPTDIR=$(cd $(dirname $0) && pwd)

grep $SCRIPTDIR/env_vars_ipa.sh /home/vagrant/.bashrc

if [ ! $? -eq 0 ]; then
    echo Configuring /home/vagrant/.bashrc
    echo source $SCRIPTDIR/env_vars_ipa.sh >> /home/vagrant/.bashrc
fi
