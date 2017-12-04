"""Synchronize DNS data with Zookeeper file system mirror."""

import glob
import logging
import os
import yaml

from treadmill import utils
from treadmill import tinydns_client

_LOGGER = logging.getLogger(__name__)


class TinyDnsSync(object):
    """Synchronizes DynDNS with Zk mirror on disk."""

    def __init__(self, cell, dns_path, domain, fs_root):
        self.cell = cell
        self.dns_client = tinydns_client.TinyDnsClient(dns_path)
        self.fs_root = fs_root

        self.domain = domain

    def _srv_rsrc(self, name, proto, endpoint, hostport):
        """Return tuple of resource endpoint/payload."""
        host, port = hostport.split(':')
        if proto not in ['tcp', 'udp']:
            _LOGGER.warn('Unsupported proto: %s', proto)
            return None

        domain = '.'.join([self.cell, 'cell', self.domain])
        url = '_%s._%s.%s.%s' % (endpoint, proto, name, domain)
        return url, host, int(port)

    def _srv_records(self, alias, pattern, endpoint):
        """Return srv records matched by pattern."""
        result = set()

        proid, app_pattern = pattern.split('.', 1)
        glob_pattern = os.path.join(self.fs_root, 'endpoints', proid,
                                    app_pattern + '#[0-9]*:*:' + endpoint)
        matching = glob.glob(glob_pattern)
        _LOGGER.debug('matching: %r', matching)

        for match in matching:
            _app, proto, _endpoint = match.split(':')
            try:
                with open(match) as f:
                    hostport = f.read()
                    srv_rec_rsrc = self._srv_rsrc(alias, proto, endpoint,
                                                  hostport)
                    if srv_rec_rsrc:
                        result.add(srv_rec_rsrc)
            except IOError:
                _LOGGER.info('Endpoint removed: %s', match)

        return result

    def _match_appgroup(self, appgroup):
        """For all endpoints that match the appgroup, add to target state."""
        _LOGGER.debug('appgroup: %r', appgroup)
        if appgroup['group-type'] != 'dns':
            return set()

        data = utils.equals_list2dict(appgroup.get('data'))
        _LOGGER.debug('data: %r', data)
        # Top level API must ensure that alias is always set, even if user
        # selects app pattern as alias (default)
        alias = data.get('alias')
        if not alias:
            _LOGGER.error('No alias supplied for %r', appgroup)
            return set()

        result = set()
        for endpoint in appgroup['endpoints']:
            srvs = self._srv_records(
                alias, appgroup['pattern'], endpoint
            )
            _LOGGER.debug('srvs: %r', srvs)
            result.update(srvs)

        return result

    def _target_records(self):
        """Returns target state as defined by zk mirror on file system."""
        target_records = set()
        appgroups_pattern = os.path.join(self.fs_root, 'app-groups', '*')
        for appgroup_f in glob.glob(appgroups_pattern):
            _LOGGER.debug('appgroup_f: %r', appgroup_f)
            if appgroup_f.startswith('.'):
                continue
            try:
                with open(appgroup_f) as f:
                    appgroup = yaml.load(f.read())
                    target_records.update(self._match_appgroup(appgroup))
            except IOError:
                _LOGGER.info('Appgroup deleted: %s', appgroup_f)

        _LOGGER.debug('target_records: %r', target_records)
        return target_records

    def sync(self):
        """Synchronizes current and target state"""
        target = self._target_records()

        _LOGGER.debug('Target state:')
        for record in sorted(target):
            _LOGGER.debug('%r', record)

        self.dns_client.clear_records()
        self.dns_client.add_ns(self.domain, 'master')

        for item in target:
            url, host, port = item
            self.dns_client.add_srv(url, host, port)

        self.dns_client.make_cdb()
