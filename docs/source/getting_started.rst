Getting Started
=========================================================================

Prerequisites
^^^^^^^^^^^^^

- VirtualBox_
- Vagrant_
- Install the `Guest Additions Plugin`_ for Vagrant

::

	vagrant plugin install vagrant-vbguest

-------------------------------------------------------------------------

Setup
^^^^^^^^^^^^^

- Clone the treadmill_ repo.
- Clone the treadmill_pid1_ repo.
- Run the following commands

::

   cd treadmill
   vagrant up --provision master
   vagrant up --provision node

-------------------------------------------------------------------------

Master
^^^^^^^^^^^^^

Once master and node are provisioned, ssh to master and node and verify the
setup. Environment is configured to run "treadmill" command.

::

   vagrant ssh master
   
   Last login: Sun Jun  4 14:07:02 2017 from 10.0.2.2
   [vagrant@master ~]$ treadmill admin ldap cell list
   name   location     version  username  root            
   local  local.local  0.1      treadmld  /opt/treadmill  


Run "treadmill admin scheduler view servers" and verify that "node" is up.

-------------------------------------------------------------------------

Node
^^^^^^^^^^^^^^

On the node, double-check that treamdill started successfully.

::

   vagrant ssh node

   Last login: Sun Jun  4 14:05:50 2017 from 10.0.2.2
   [vagrant@node ~]$ cd /var/tmp/treadmill/init/server_init/log/
   [vagrant@node log]$ tail -F current 
   2017-06-04 14:02:26.254208500  DEBUG    [MainThread] treadmill.iptables:234 - Reloading Treadmill filter rules (drop all NONPROD)
   2017-06-04 14:02:26.254218500  DEBUG    [MainThread] treadmill.subproc:216 - invoke: ['iptables_restore', '--noflush']
   2017-06-04 14:02:26.493017500  DEBUG    [MainThread] treadmill.runtime.linux.image.fs:60 - Creating an extention manager for 'treadmill.image.native.fs'.
   2017-06-04 14:02:29.018783500  INFO     [MainThread] treadmill.runtime.linux.image.fs:85 - There are no fs plugins for image 'native'.
   2017-06-04 14:02:29.046411500  DEBUG    [MainThread] treadmill.runtime.linux.image.fs:60 - Creating an extention manager for 'treadmill.image.tar.fs'.
   2017-06-04 14:02:29.046422500  INFO     [MainThread] treadmill.runtime.linux.image.fs:85 - There are no fs plugins for image 'tar'.
   2017-06-04 14:02:29.046423500  DEBUG    [MainThread] treadmill.runtime.linux.image.fs:60 - Creating an extention manager for 'treadmill.image.docker.fs'.
   2017-06-04 14:02:29.046424500  INFO     [MainThread] treadmill.runtime.linux.image.fs:85 - There are no fs plugins for image 'docker'.
   2017-06-04 14:02:29.046425500  DEBUG    [MainThread] treadmill.netdev:486 - Setting '/proc/sys/net/ipv4/conf/tm0/forwarding' to 1
   2017-06-04 14:02:29.046425500  INFO     [MainThread] treadmill.sproc.init:81 - Ready.


-------------------------------------------------------------------------

Schedule an App (e.g. python webserver - port 8000 )
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   treadmill admin master app schedule --env prod --proid treadmld --manifest treadmill/infra/manifests/python_server.yml treadmld.foo


-------------------------------------------------------------------------

Trace
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   treadmill admin trace <appname>

-------------------------------------------------------------------------

Discovery
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   treadmill admin discovery <appname> --check-state

-------------------------------------------------------------------------

SSH
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   treadmill admin ssh <appname>

-------------------------------------------------------------------------


.. _VirtualBox: https://www.virtualbox.org/wiki/Downloads
.. _Vagrant: https://www.vagrantup.com/docs/installation/
.. _Guest Additions Plugin: https://github.com/dotless-de/vagrant-vbguest
.. _treadmill: https://github.com/MorganStanley/treadmill
.. _treadmill_pid1: https://github.com/MorganStanley/treadmill-pid1
