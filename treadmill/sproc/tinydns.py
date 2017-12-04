"""
Treadmill app-dns daemon for TinyDNS.

Synchronize DNS with local mirror of Zookeeper data.
"""

import logging
import os
import time

import click

from treadmill import context
from treadmill import tinydns_sync
from treadmill import zkutils
from treadmill import zknamespace as z

_LOGGER = logging.getLogger(__name__)


def init():
    """Treadmill App DNS for TinyDNS"""

    @click.command(name='tinydns')
    @click.option('--fs-root',
                  help='Root file system directory to zk2fs',
                  required=True)
    @click.option('--dns-root',
                  help='Path to tinyDNS root folder',
                  required=True)
    @click.option('--no-lock', is_flag=True, default=False,
                  help='Run without lock.')
    def tinydns(fs_root, dns_root, no_lock):
        """Start Treadmill Add DNS"""
        cell = context.GLOBAL.cell

        fqdn = context.GLOBAL.dns_domain

        modified = os.path.join(fs_root, '.modified')
        while not os.path.exists(modified):
            _LOGGER.info('zk2fs mirror does not exist, waiting')
            time.sleep(1)

        sync = tinydns_sync.TinyDnsSync(cell, dns_root, fqdn, fs_root)

        def _run():
            """Run sync process."""
            modified_at = 0
            while True:
                new_modified = os.stat(modified).st_mtime
                if new_modified > modified_at:
                    sync.sync()
                    modified_at = new_modified

                time.sleep(5)

        if not no_lock:
            lock = zkutils.make_lock(context.GLOBAL.zk.conn,
                                     z.path.election(__name__))

            _LOGGER.info('Waiting for leader lock.')
            with lock:
                _run()

        else:
            _LOGGER.info("Running without lock.")
            _run()

    return tinydns
