#/bin/bash

SCRIPTDIR=$(cd $(dirname $0) && pwd)
. $SCRIPTDIR/svc_utils.sh

DNS=/usr/local/bin

mkdir -p /package
chmod 1755 /package

cd /package
wget https://cr.yp.to/ucspi-tcp/ucspi-tcp-0.88.tar.gz
gunzip ucspi-tcp-0.88.tar.gz
tar -xf ucspi-tcp-0.88.tar
rm -f ucspi-tcp-0.88.tar
cd ucspi-tcp-0.88
echo gcc -O2 -include /usr/include/errno.h > conf-cc
make
make setup check

cd /package
wget https://cr.yp.to/djbdns/djbdns-1.05.tar.gz
gunzip djbdns-1.05.tar.gz
tar -xf djbdns-1.05.tar
rm -f djbdns-1.05.tar
cd djbdns-1.05
echo gcc -O2 -include /usr/include/errno.h > conf-cc
make
make setup check

$DNS/tinydns-conf tinydns tinydnslog /etc/tinydns 10.10.10.10

$DNS/axfrdns-conf tinydnstcp tinydnslog /etc/axfrdns /etc/tinydns \
  10.10.10.10
echo ':allow,AXFR=""' > /etc/axfrdns/tcp

cd /etc/axfrdns
$DNS/tcprules tcp.cdb tcp.tmp < tcp

del_svc tinydns
del_svc tinydns-tcp
del_svc zk2fs
del_svc tinydns-app

add_svc tinydns
add_svc tinydns-tcp
add_svc zk2fs
add_svc tinydns-app
