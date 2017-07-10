"""Treadmill app configurator daemon, subscribes to eventmgr events.
"""

import click

from treadmill import appcfgmgr


def init():
    """Top level command handler."""

    @click.command()
    @click.option('--approot', type=click.Path(exists=True),
                  envvar='TREADMILL_APPROOT', required=True)
    @click.option('--runtime', envvar='TREADMILL_RUNTIME', required=True)
    def top(approot, runtime):
        """Starts appcfgmgr process."""
        mgr = appcfgmgr.AppCfgMgr(approot, runtime)
        mgr.run()

    return top
