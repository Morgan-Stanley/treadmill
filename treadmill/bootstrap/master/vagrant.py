"""Vagrant specific install profile."""

from .. import vagrant_aliases as aliases

DEFAULTS = {
    'treadmill_dns_domain': 'treadmill.internal',
    'treadmill_dns_server': '10.10.10.10'
}

ALIASES = aliases.ALIASES
