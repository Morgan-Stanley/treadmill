"""Vagrant specific install profile."""

from .. import vagrant_aliases as aliases

DEFAULTS = {
    'network_device': 'eth1',
    'treadmill_cpu': '90%',
    'treadmill_cpu_cores': 0,
    'treadmill_mem': '-1G',
    'treadmill_core_mem': '1G',
    'treadmill_dns_domain': 'treadmill.internal',
    'treadmill_dns_server': '10.10.10.10',
    'localdisk_img_location': '{{ dir }}',
    'localdisk_img_size': '-2G',
    'localdisk_block_dev': None,
    'localdisk_default_read_bps': '20M',
    'localdisk_default_read_iops': '100',
    'localdisk_default_write_bps': '20M',
    'localdisk_default_write_iops': '100',
}

ALIASES = aliases.ALIASES
