"""
Unit test for tinyDNS client
treadmill.tinydns_client
"""

import os
import shutil
import tempfile
import unittest

from treadmill import tinydns_client


class tinydns_clientTest(unittest.TestCase):
    """Tests for treadmill.tinydns_client"""

    def setUp(self):
        """Setup test"""
        self.dns_folder = tempfile.mkdtemp()
        self.dns_data = os.path.join(self.dns_folder, 'data')

        if not os.path.exists(self.dns_data):
            open(self.dns_data, 'w').close()

    def tearDown(self):
        """Tear down test"""
        if self.dns_folder and os.path.isdir(self.dns_folder):
            shutil.rmtree(self.dns_folder)

    def test_process_number(self):
        """Tests processing numbers to octal"""
        client = tinydns_client.TinyDnsClient(self.dns_folder)

        low_number_out = client.process_number(128)
        self.assertEqual(low_number_out, '\\000\\200')

        high_number_out = client.process_number(8000)
        self.assertEqual(high_number_out, '\\037\\100')

    def test_process_target(self):
        """Tests processing target records"""
        client = tinydns_client.TinyDnsClient(self.dns_folder)

        target = client.process_target('worker.treadmill-dev.xx.com')
        self.assertEqual(target,
                         '\\006worker\\015treadmill-dev\\002xx\\003com')

    def test_clear_records(self):
        """Tests clearing records"""
        with open(self.dns_data, 'w') as f:
            f.write("test")

        client = tinydns_client.TinyDnsClient(self.dns_folder)
        client.clear_records()
        self.assertTrue(os.stat(self.dns_data).st_size == 0)

    def test_add_ns(self):
        """Tests adding name server records"""
        client = tinydns_client.TinyDnsClient(self.dns_folder)
        client.clear_records()

        client.add_ns('treadmill-dev.xx.com', '10.10.10.10')
        with open(os.path.join(self.dns_folder, 'data'), 'r') as f:
            ns_record = f.read()

        self.assertEqual(ns_record,
                         '.treadmill-dev.xx.com:10.10.10.10:a:600\n')

    def test_add_srv(self):
        """Tests adding srv records"""
        client = tinydns_client.TinyDnsClient(self.dns_folder)
        client.clear_records()

        client.add_srv('_http._tcp.api.treadmill-dev.xx.com',
                       'worker.treadmill-dev.xx.com', 35956)
        with open(os.path.join(self.dns_folder, 'data'), 'r') as f:
            srv_record = f.read()

        expected_srv = (":_http._tcp.api.treadmill-dev.xx.com:33:"
                        "\\000\\012\\000\\012\\214\\164\\006worker"
                        "\\015treadmill-dev\\002xx\\003com\\000:60\n")

        self.assertEqual(srv_record, expected_srv)


if __name__ == '__main__':
    unittest.main()
