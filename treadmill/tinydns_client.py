"""Script to add DNS records to TinyDNS"""

import logging
import os
import subprocess

DEFAULT_NS_TTL = 600
DEFAULT_TTL = 60
DEFAULT_WEIGHT = 10
DEFAULT_PRIORITY = 10

_LOGGER = logging.getLogger(__name__)


class TinyDnsClient(object):
    """Helper class to call tinyDNS"""

    def __init__(self, dns_path):
        self.dns_path = dns_path
        self.dns_data = os.path.join(dns_path, 'data')

    def process_number(self, number):
        """Process number for TinyDNS records. Represents number in 3 length
        octals. If number is larger than 256, the first octal represents
        multiples of 256 and the second represents the leftover."""
        high_number = 0
        if number - 256 >= 0:
            high_number = int(number / 256)
            number -= high_number * 256
        output = r'\%.3o' % high_number
        output += r'\%.3o' % number
        return output

    def process_target(self, target):
        """Replaces the periods in target record with a 3 length octal
        representing the length of the block"""
        output = ""
        target_blocks = target.split('.')
        for block in target_blocks:
            output += r'\%.3o' % len(block) + block
        return output

    def add_ns(self, record, addr, ttl=DEFAULT_NS_TTL):
        """Add a Name Server record"""
        ns_format = '.%s:%s:a:%d\n'
        with open(self.dns_data, 'a') as f:
            f.write(ns_format % (record, addr, ttl))

    def add_srv(self, record, target, port, prio=DEFAULT_PRIORITY,
                weight=DEFAULT_WEIGHT, ttl=DEFAULT_TTL):
        """Add a SRV record"""
        # 33 indicates SRV record
        # \000 indicates end of target name
        srv_format = r':%s:33:%s%s%s%s\000:%d'
        prio = self.process_number(prio)
        weight = self.process_number(weight)
        port = self.process_number(port)
        target = self.process_target(target)
        with open(self.dns_data, 'a') as f:
            f.write(srv_format % (record, prio, weight, port, target, ttl))
            f.write('\n')

    def make_cdb(self):
        """Calls the make file used by TinyDNS to create the data.cdb file used to
        find DNS records"""
        subprocess.Popen(['make'], stdout=subprocess.PIPE, cwd=self.dns_path)

    def clear_records(self):
        """Clear all stored records"""
        open(self.dns_data, 'w').close()
