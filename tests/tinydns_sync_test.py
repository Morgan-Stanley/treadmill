"""
Unit test for DNS API, i.e. treadmill.dns.
"""

import os
import shutil
import tempfile
import unittest
import mock

from treadmill import tinydns_sync
from treadmill import tinydns_client


class DnsSyncTest(unittest.TestCase):
    """Tests for treadmill.dns"""

    def setUp(self):
        """Setup test"""
        self.root = tempfile.mkdtemp()
        self.dns_folder = tempfile.mkdtemp()

    def tearDown(self):
        """Tear down test"""
        if self.root and os.path.isdir(self.root):
            shutil.rmtree(self.root)
        if self.dns_folder and os.path.isdir(self.dns_folder):
            shutil.rmtree(self.dns_folder)

    @mock.patch('treadmill.tinydns_client.TinyDnsClient.add_srv',
                mock.Mock())
    @mock.patch('treadmill.tinydns_client.TinyDnsClient.add_ns',
                mock.Mock())
    @mock.patch('treadmill.tinydns_client.TinyDnsClient.clear_records',
                mock.Mock())
    @mock.patch('treadmill.tinydns_client.TinyDnsClient.make_cdb',
                mock.Mock())
    def test_sync(self):
        """Tests sync operation"""
        endpoints_dir = os.path.join(self.root, 'endpoints', 'treadmld')
        os.makedirs(endpoints_dir)
        with open(os.path.join(endpoints_dir,
                               'api#0000000013:tcp:http'), 'w+') as f:
            f.write('worker1.treadmill-dev.xx.com:35956')
        with open(os.path.join(endpoints_dir,
                               'api#0000000013:tcp:ssh'), 'w+') as f:
            f.write('worker1.treadmill-dev.xx.com:35542')

        appgroup_dir = os.path.join(self.root, 'app-groups')
        os.makedirs(appgroup_dir)
        with open(os.path.join(appgroup_dir, 'treadmld.api'), 'w+') as f:
            f.write("""
                    cells: [testcell]
                    data: [alias=api]
                    endpoints: [http]
                    group-type: dns
                    pattern: treadmld.api
                    """)
        sync = tinydns_sync.TinyDnsSync('testcell', self.dns_folder,
                                        'treadmill-dev.xx.com', self.root)
        sync.ip = '10.10.10.10'
        sync.sync()

        tinydns_client.TinyDnsClient.add_ns.assert_has_calls([
            mock.call('treadmill-dev.xx.com', 'master')
        ])

        tinydns_client.TinyDnsClient.add_srv.assert_has_calls([
            mock.call(
                '_http._tcp.api.testcell.cell.treadmill-dev.xx.com',
                'worker1.treadmill-dev.xx.com', 35956
            ),
        ])


if __name__ == '__main__':
    unittest.main()
