"""Unit test for treadmill.appcfg.manifest
"""

import os
import shutil
import tempfile
import unittest

import mock

import treadmill
from treadmill import context
from treadmill import exc

from treadmill.appcfg import manifest as app_manifest


class AppCfgManifestTest(unittest.TestCase):
    """Tests for teadmill.appcfg.manifest"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        context.GLOBAL.cell = 'testcell'
        context.GLOBAL.zk.url = 'zookeeper://foo@foo:123'
        self.tm_env = mock.Mock(
            cell='testcell',
            zkurl='zookeeper://foo@foo:123',
        )

    def tearDown(self):
        if self.root and os.path.isdir(self.root):
            shutil.rmtree(self.root)

    @mock.patch('treadmill.appcfg.gen_uniqueid', mock.Mock(return_value='42'))
    @mock.patch('treadmill.appcfg.manifest.read', mock.Mock())
    @mock.patch('treadmill.subproc._check', mock.Mock(return_value=True))
    @mock.patch('treadmill.subproc.get_aliases',
                mock.Mock(return_value={
                    'mkdir': '/path/to/mkdir',
                    'chmod': '/path/to/chmod',
                    'sshd': '/path/to/sshd'}))
    def test_load(self):
        """Tests loading app manifest with resource allocation."""
        manifest = {
            'services': [
                {
                    'name': 'web_server',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    },
                },
            ],
            'proid': 'foo',
            'environment': 'dev',
            'disk': '100G',
            'cpu': '100%',
            'memory': '100M'
        }

        treadmill.appcfg.manifest.read.return_value = manifest
        event_filename0 = os.path.join(self.root, 'proid.myapp#0')

        app0 = app_manifest.load(self.tm_env, event_filename0)

        treadmill.appcfg.manifest.read.assert_called_with(event_filename0,
                                                          'yaml')
        treadmill.appcfg.gen_uniqueid.assert_called_with(event_filename0)
        self.assertEqual(app0['name'], 'proid.myapp#0')
        self.assertEqual(app0['type'], 'native')
        self.assertEqual(app0['app'], 'proid.myapp')
        self.assertEqual(app0['proid'], 'foo')
        self.assertEqual(app0['environment'], 'dev')
        self.assertEqual(app0['cpu'], 100)
        self.assertEqual(app0['memory'], '100M')
        self.assertEqual(app0['disk'], '100G')
        self.assertEqual(
            app0['services'],
            [
                {
                    'name': 'web_server',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    },
                    'root': False,
                },
            ]
        )
        self.assertEqual(
            app0['system_services'],
            [
                {
                    'command': (
                        '/path/to/mkdir -p /var/empty/sshd && '
                        '/path/to/chmod 0755 /var/empty/sshd && '
                        'exec /path/to/sshd -D -f /etc/ssh/sshd_config'
                        ' -p $TREADMILL_ENDPOINT_SSH'
                    ),
                    'name': 'sshd',
                    'proid': None,
                    'restart': {
                        'interval': 60,
                        'limit': 5,
                    },
                },
            ],
        )
        self.assertEqual(
            app0['endpoints'],
            [
                {
                    'name': 'ssh',
                    'port': 0,
                    'proto': 'tcp',
                    'type': 'infra',
                },
            ]
        )
        self.assertEqual(app0['uniqueid'], '42')
        self.assertEqual(app0['cell'], 'testcell')
        self.assertEqual(app0['zookeeper'], 'zookeeper://foo@foo:123')

    @mock.patch('treadmill.appcfg.gen_uniqueid', mock.Mock(return_value='42'))
    @mock.patch('treadmill.appcfg.manifest.read', mock.Mock())
    @mock.patch('treadmill.subproc._check', mock.Mock(return_value=True))
    @mock.patch('treadmill.subproc.get_aliases',
                mock.Mock(return_value={
                    'mkdir': '/path/to/mkdir',
                    'chmod': '/path/to/chmod',
                    'sshd': '/path/to/sshd'}))
    def test_load_normalize(self):
        """Test the normalization of manifests.
        """
        manifest = {
            'services': [
                {
                    'name': 'test1',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    }
                },
                {
                    'name': 'test2',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    }
                },
            ],
            'endpoints': [
                {
                    'name': 'test1',
                    'proto': 'udp',
                    'port': 12345,
                },
                {
                    'name': 'test2',
                    'port': '0',
                },
                {
                    'name': 'test3',
                    'port': 32,
                    'type': 'infra',
                },
            ],
            'ephemeral_ports': {
                'tcp': '2',
            },
            'proid': 'foo',
            'environment': 'dev',
            'disk': '100G',
            'cpu': '100%',
            'memory': '100M'
        }
        treadmill.appcfg.manifest.read.return_value = manifest
        event_filename0 = os.path.join(self.root, 'proid.myapp#0')

        app0 = app_manifest.load(self.tm_env, event_filename0)

        self.assertEqual(app0['type'], 'native')
        self.assertEqual(
            app0['services'],
            [
                {
                    'name': 'test1',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    },
                    'root': False,
                },
                {
                    'name': 'test2',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    },
                    'root': False,
                },
            ]
        )
        self.assertEqual(
            app0['system_services'],
            [
                {
                    'command': (
                        '/path/to/mkdir -p /var/empty/sshd && '
                        '/path/to/chmod 0755 /var/empty/sshd && '
                        'exec /path/to/sshd'
                        ' -D -f /etc/ssh/sshd_config'
                        ' -p $TREADMILL_ENDPOINT_SSH'
                    ),
                    'name': 'sshd',
                    'proid': None,
                    'restart': {
                        'limit': 5,
                        'interval': 60,
                    },
                },
            ]
        )
        self.assertEqual(app0['shared_ip'], False)
        self.assertEqual(app0['shared_network'], False)
        self.assertEqual(
            app0['endpoints'],
            [
                {
                    'name': 'test1',
                    'type': None,
                    'port': 12345,
                    'proto': 'udp',
                },
                {
                    'name': 'test2',
                    'type': None,
                    'port': 0,
                    'proto': 'tcp',
                },
                {
                    'name': 'test3',
                    'type': 'infra',
                    'port': 32,
                    'proto': 'tcp',
                },
                {
                    'name': 'ssh',
                    'type': 'infra',
                    'port': 0,
                    'proto': 'tcp',
                },
            ]
        )
        self.assertEqual(app0['passthrough'], [])
        self.assertEqual(app0['vring']['cells'], [])
        self.assertEqual(app0['identity'], None)
        self.assertEqual(app0['identity_group'], None)
        self.assertEqual(app0['environ'], [])
        self.assertEqual(app0['ephemeral_ports'], {'tcp': 2, 'udp': 0})

    @mock.patch('treadmill.appcfg.gen_uniqueid', mock.Mock(return_value='42'))
    @mock.patch('treadmill.appcfg.manifest.read', mock.Mock())
    @mock.patch('treadmill.subproc._check', mock.Mock(return_value=True))
    @mock.patch('treadmill.subproc.get_aliases',
                mock.Mock(return_value={
                    'mkdir': '/path/to/mkdir',
                    'chmod': '/path/to/chmod',
                    'sshd': '/path/to/sshd'}))
    def test_load_with_env(self):
        """Tests loading app manifest with resource allocation."""
        manifest = {
            'services': [
                {
                    'name': 'web_server',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    }
                }
            ],
            'proid': 'foo',
            'environment': 'dev',
            'disk': '100G',
            'cpu': '100%',
            'memory': '100M',
            'environ': [
                {'name': 'xxx', 'value': 'yyy'}
            ],
        }

        treadmill.appcfg.manifest.read.return_value = manifest
        event_filename0 = os.path.join(self.root, 'proid.myapp#0')

        app0 = app_manifest.load(self.tm_env, event_filename0)
        self.assertEqual(app0['environ'], [{'name': 'xxx', 'value': 'yyy'}])

    @mock.patch('treadmill.appcfg.gen_uniqueid', mock.Mock(return_value='42'))
    @mock.patch('treadmill.appcfg.manifest.read', mock.Mock())
    @mock.patch('treadmill.subproc._check', mock.Mock(return_value=True))
    @mock.patch('treadmill.subproc.get_aliases',
                mock.Mock(return_value={
                    'mkdir': '/path/to/mkdir',
                    'chmod': '/path/to/chmod',
                    'sshd': '/path/to/sshd'}))
    def test_load_docker_image(self):
        """Tests loading app manifest with a docker image defined."""
        manifest = {
            'proid': 'foo',
            'environment': 'dev',
            'disk': '100G',
            'cpu': '100%',
            'memory': '100M',
            'image': 'docker://test'
        }

        treadmill.appcfg.manifest.read.return_value = manifest
        event_filename0 = os.path.join(self.root, 'proid.myapp#0')

        app0 = app_manifest.load(self.tm_env, event_filename0)
        self.assertEqual(app0['image'], 'docker://test')
        self.assertEqual(app0['type'], 'docker')

    @mock.patch('treadmill.appcfg.gen_uniqueid', mock.Mock(return_value='42'))
    @mock.patch('treadmill.appcfg.manifest.read', mock.Mock())
    @mock.patch('treadmill.subproc._check', mock.Mock(return_value=True))
    @mock.patch('treadmill.subproc.get_aliases',
                mock.Mock(return_value={
                    'mkdir': '/path/to/mkdir',
                    'chmod': '/path/to/chmod',
                    'sshd': '/path/to/sshd'}))
    def test_load_tar_image(self):
        """Tests loading app manifest with a docker image defined."""
        manifest = {
            'services': [
                {
                    'name': 'web_server',
                    'command': '/bin/sleep 5',
                    'restart': {
                        'limit': 3,
                        'interval': 60,
                    }
                }
            ],
            'proid': 'foo',
            'environment': 'dev',
            'disk': '100G',
            'cpu': '100%',
            'memory': '100M',
            'image': 'http://test'
        }

        treadmill.appcfg.manifest.read.return_value = manifest
        event_filename0 = os.path.join(self.root, 'proid.myapp#0')

        app0 = app_manifest.load(self.tm_env, event_filename0)
        self.assertEqual(app0['image'], 'http://test')
        self.assertEqual(app0['type'], 'tar')

        manifest = {
            'proid': 'foo',
            'disk': '100G',
            'cpu': '100%',
            'memory': '100M',
            'image': 'http://test'
        }

        treadmill.appcfg.manifest.read.return_value = manifest

        with self.assertRaises(exc.InvalidInputError):
            app_manifest.load(self.tm_env, event_filename0)


if __name__ == '__main__':
    unittest.main()
