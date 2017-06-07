#!/bin/sh

# Start root supervisor.

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

set -e

function add_svc {
    echo Adding service: $1
    cp -v /home/vagrant/treadmill/vagrant/systemd/$1.service \
        /etc/systemd/system/

    /bin/systemctl daemon-reload
    /bin/systemctl enable $1.service --now
}

function del_svc {
    echo Deleting service: $1
    /bin/systemctl disable $1.service --now || /bin/true
    rm -vrf /etc/systemd/system/$1.service
    /bin/systemctl daemon-reload
}

# Source environment variables.
SCRIPTDIR=$(cd $(dirname $0) && pwd)

source $SCRIPTDIR/env_vars.sh

TM=/opt/treadmill/bin/treadmill

echo Installing openldap

del_svc openldap

/opt/s6/bin/s6-setuidgid treadmld \
    $TM admin install --install-dir /var/tmp/treadmill-openldap \
        openldap \
        --owner treadmld \
        --uri ldap://master:22389 \
        --suffix dc=local \
        --rootpw $(/usr/sbin/slappasswd -s secret)

add_svc openldap

echo Initializing openldap
sleep 3


/opt/s6/bin/s6-setuidgid treadmld \
    $TM admin ldap init

/opt/s6/bin/s6-setuidgid treadmld \
    $TM admin ldap schema --update

echo Configuring local cell

/opt/s6/bin/s6-setuidgid treadmld \
    $TM admin ldap cell configure local --version 0.1 --root /opt/treadmill \
        --username treadmld \
        --location local.local \

# For simplicity, use default zookeeper port - 2181. This way default
# install of zookeeper tools will just work.
#
# This is single node Zookeeper install, no need to specify additional
# ports.
/opt/s6/bin/s6-setuidgid treadmld \
    $TM admin ldap cell insert local --idx 1 --hostname master \
        --client-port 2181

# Add server to the cell.
/opt/s6/bin/s6-setuidgid treadmld \
    $TM admin ldap server configure node --cell local

echo Extracting cell config

$TM --outfmt yaml admin ldap cell configure local >/var/tmp/cell_conf.yml

echo Installing zookeper

del_svc zookeeper

/opt/s6/bin/s6-setuidgid treadmld \
    $TM admin install \
        --install-dir /var/tmp/treadmill-zookeeper \
        --config /var/tmp/cell_conf.yml \
        zookeeper \
        --master-id 1

add_svc zookeeper

echo Installing Treadmill Master

del_svc treadmill-master

$TM admin install \
    --install-dir /var/tmp/treadmill-master \
    --config /var/tmp/cell_conf.yml \
    master \
    --master-id 1 \
    --ldap-pwd secret

add_svc treadmill-master
