#!/bin/sh

echo 127.0.0.1   localhost   > /etc/hosts
echo 10.10.10.10 master.ms.local    master     >> /etc/hosts
echo 10.10.10.11 node.ms.local    node       >> /etc/hosts
echo 10.10.10.12 ipa.ms.local    ipa    >> /etc/hosts
