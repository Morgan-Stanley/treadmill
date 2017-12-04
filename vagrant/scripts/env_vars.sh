# Configure environment variables.

# Setup environment vars
(
    cat <<EOF
export TREADMILL_ZOOKEEPER=zookeeper://foo@master:2181
export TREADMILL_CELL=local
export TREADMILL_DNS_DOMAIN=treadmill.internal
export TREADMILL_DNS_SERVER=10.10.10.10
export TREADMILL_LDAP=ldap://master:22389
export TREADMILL_LDAP_SUFFIX=dc=local
export TREADMILL_LDAP_PWD=secret
export TREADMILL_LDAP_USER=cn=Manager,cn=config
export TREADMILL_DNS_DOMAIN=treadmill.org
export TREADMILL_PROFILE=vagrant
export TREADMILL=/opt/treadmill
export LC_ALL=en_US.utf8
export LANG=en_US.utf8
export PATH=$PATH:/opt/s6/bin:/opt/treadmill/bin
EOF
) >> /etc/profile.d/treadmill_profile.sh

source /etc/profile.d/treadmill_profile.sh
