#!/bin/bash

set -e

echo Installing ipa packages.

yum -y install policycoreutils-python

# Disable SELinux until we figure out services start
echo -e 'SELINUX=permissive\nSELINUXTYPE=targeted\n' >/etc/sysconfig/selinux
/sbin/setenforce 0

if [ ! -e /etc/yum.repos.d/treadmill.repo ]; then
    curl -L https://s3.amazonaws.com/yum_repo_dev/treadmill.repo -o /etc/yum.repos.d/treadmill.repo
fi

# Install S6, pid1
yum install s6 execline treadmill-pid1 --nogpgcheck -y

