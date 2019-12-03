#!/bin/bash

yum install -y ipa-server haveged ipa-server-dns

systemctl enable haveged
systemctl start haveged

PRIVATE_IP=$(ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/')
IPA_ADMIN_PASSWORD="Tre@dmill1"
DOMAIN="ms.local"
REALM="MS.LOCAL"
TM=/opt/treadmill/bin/treadmill

ipa-server-install --unattended \
    --no-ntp --mkhomedir \
    --domain "$DOMAIN" \
    --realm "$REALM" \
    -a "$IPA_ADMIN_PASSWORD" \
    -p "$IPA_ADMIN_PASSWORD" \
    --setup-dns \
    --reverse-zone="10.10.10.in-addr.arpa." \
    --forwarder "8.8.8.8" \
    --ip-address "${PRIVATE_IP}" \
    --allow-zone-overlap \

echo "$IPA_ADMIN_PASSWORD" | kinit admin

ipa dnszone-mod "$DOMAIN" --allow-sync-ptr=TRUE

ipa dnsrecord-add "$DOMAIN" ipa-ca --a-rec ${PRIVATE_IP}

TMHOSTADM_OUTPUT=$(ipa -n user-add tmhostadm --first tmhostadm --last proid --shell /bin/bash --class proid --random)
TMP_TMHOSTADM_PASSWORD=$(echo "${TMHOSTADM_OUTPUT}" | grep 'Random password:' | awk '{print $3}')
NEW_TMHOSTADM_PASSWORD=$(openssl rand -base64 12)

kpasswd tmhostadm <<EOF
${TMP_TMHOSTADM_PASSWORD}
${NEW_TMHOSTADM_PASSWORD}
${NEW_TMHOSTADM_PASSWORD}
EOF

ipa role-add "Host Enroller" --desc "Host Enroller"
ipa role-add-privilege "Host Enroller" --privileges "Host Enrollment"
ipa role-add-privilege "Host Enroller" --privileges "Host Administrators"
ipa role-add-member "Host Enroller" --users tmhostadm

ipa role-add "Service Admin" --desc "Service Admin"
ipa role-add-privilege "Service Admin" --privileges "Service Administrators"
ipa role-add-member "Service Admin" --users tmhostadm

kadmin.local -q "xst -norandkey -k /tmp/tmhostadm.keytab tmhostadm"
chown tmhostadm:tmhostadm /tmp/tmhostadm.keytab

(
cat <<EOF
su -c "kinit -k -t /tmp/tmhostadm.keytab tmhostadm" tmhostadm
EOF
) > /etc/cron.hourly/tmhostadm-kinit

chmod 755 /etc/cron.hourly/tmhostadm-kinit
/etc/cron.hourly/tmhostadm-kinit

export TREADMILL_CELL="local"

nohup su -c "$TM sproc restapi -p 8000 --title 'Treadmill_IPA_API' \
    -m ipa --cors-origin='.*'" tmhostadm > /var/log/ipa_api.out 2>&1 &

TREADMLD_OUTPUT=$(ipa -n user-add --first=treadmld --last=proid --shell /bin/bash --class proid --random treadmld)
TMP_TREADMLD_PASSWORD=$(echo "${TREADMLD_OUTPUT}" | grep 'Random password:' | awk '{print $3}')
NEW_TREADMLD_PASSWORD=$(openssl rand -base64 12)

kpasswd treadmld <<EOF
${TMP_TREADMLD_PASSWORD}
${NEW_TREADMLD_PASSWORD}
${NEW_TREADMLD_PASSWORD}
EOF
