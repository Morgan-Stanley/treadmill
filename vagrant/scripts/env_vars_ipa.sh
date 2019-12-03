# Configure environment variables.

# Setup environment vars
(
    cat <<EOF
export TREADMILL_ZOOKEEPER=zookeeper://foo@master.ms.local:2181
export TREADMILL_CELL=local
export TREADMILL_LDAP=ldap://master.ms.local:22389
export TREADMILL_LDAP_SUFFIX=dc=ms,dc=local
export TREADMILL=/opt/treadmill
export LC_ALL=en_US.utf8
export LANG=en_US.utf8
export PATH=$PATH:/opt/s6/bin:/opt/treadmill/bin
EOF
) >> /etc/profile.d/treadmill_profile.sh

source /etc/profile.d/treadmill_profile.sh
