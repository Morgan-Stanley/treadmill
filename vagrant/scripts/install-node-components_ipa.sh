#!/bin/sh

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

set -e

# Source environment variables.
SCRIPTDIR=$(cd $(dirname $0) && pwd)

source $SCRIPTDIR/env_vars_ipa.sh

. $SCRIPTDIR/svc_utils_ipa.sh

TM=/opt/treadmill/bin/treadmill

kinit -kt /etc/krb5.keytab

echo Extracting cell config

$TM --outfmt yaml admin ldap cell configure local >/var/tmp/cell_conf.yml

(
cat <<EOF
mkdir -p /var/spool/tickets
kinit -k -t /etc/krb5.keytab -c /var/spool/tickets/treadmld
chown treadmld:treadmld /var/spool/tickets/treadmld
EOF
) > /etc/cron.hourly/hostkey-treadmld-kinit

chmod 755 /etc/cron.hourly/hostkey-treadmld-kinit
/etc/cron.hourly/hostkey-treadmld-kinit

echo Installing Treadmill Node

del_svc treadmill-node

$TM admin install \
    --install-dir /var/tmp/treadmill-node \
    --install-dir /var/tmp/treadmill \
    --config /var/tmp/cell_conf.yml \
    node

ln -s /var/spool/tickets/treadmld /var/tmp/treadmill/spool/krb5cc_host

add_svc treadmill-node
