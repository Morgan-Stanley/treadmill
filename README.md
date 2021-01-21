# Treadmill

[![Build Status](https://travis-ci.com/MorganStanley/treadmill.svg?branch=master)](https://travis-ci.com/MorganStanley/treadmill)
## Download
```shell
wget https://github.com/MorganStanley/treadmill/releases/download/0.0.1/treadmill -O /usr/bin/treadmill && chmod +x /usr/bin/treadmill
```
This will put `treadmill` in your path.

## Vagrant setup for development

### Prerequisites
* [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
* [Vagrant](https://www.vagrantup.com/docs/installation/)
* Install the [Guest Additions plugin](https://github.com/dotless-de/vagrant-vbguest) for Vagrant
``` sh
vagrant plugin install vagrant-vbguest
```
### Vagrant Setup
* Clone the [treadmill](https://github.com/MorganStanley/treadmill.git) repo.
* Clone the [treadmill-pid1](https://github.com/MorganStanley/treadmill-pid1) repo.
* Run the following commands
``` sh
cd treadmill
git checkout standard_setup
vagrant up
vagrant ssh
```
* Create the cgroup folders as root
``` sh
sudo su -
cd /sys/fs/cgroup
for i in *; do mkdir -p $i/treadmill/apps $i/treadmill/core $i/system ; done
cd -
```
* Start the zookeeper service
``` sh
cd /home/centos && zookeeper-3.4.9/bin/zkServer.sh start
```
* Make the mount private
``` sh
sudo mount --make-rprivate /
```
* Treadmill should now be available on the box
``` sh
source /home/centos/env/bin/activate
treadmill --help
```


### Treadmill cli cheatsheet
``` sh
treadmill sproc scheduler /tmp
treadmill sproc service --root-dir /tmp/treadmill/ localdisk --reserve 20G --img-location /tmp/treadmill --default-read-bps 100M --default-write-bps 100M --default-read-iops 300 --default-write-iops 300
treadmill sproc service --root-dir /tmp/treadmill/ network
treadmill sproc service --root-dir /tmp/treadmill/ cgroup

# Zookeeper shell
create /scheduled/centos.bar#123 {"memory":"100M","cpu":"10%","disk":"500M","proid":"centos","affinity":"centos.bar","services":[{"name":"sleep","command":"/bin/top","restart":{"limit":5,"interval":60}}]}
create /servers/localhost.localdomain {"parent":"all:unknown","features":[],"traits":[],"label":null,"valid_until":1488573090.0}
create /cell/all:unknown {}
create /buckets/all:unknown {"parent":null,"traits":0}

# System shell
treadmill sproc init --approot /tmp/treadmill/
cd /tmp/treadmill/running && nohup /bin/s6-svscan > s6_svscan.out & && cd -
treadmill sproc eventdaemon
treadmill sproc appcfgmgr
```
