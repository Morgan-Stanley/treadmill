"""Installs and configures Treadmill locally.
"""

import logging
import os

import click

from treadmill import bootstrap


_LOGGER = logging.getLogger(__name__)


def init():
    """Return top level command handler."""

    @click.command()
    @click.option('--run/--no-run', is_flag=True, default=False)
    @click.option('--master-id', required=True,
                  type=click.Choice(['1', '2', '3']))
    @click.pass_context
    def zookeeper(ctx, run, master_id):
        """Installs Treadmill master."""

        ctx.obj['PARAMS']['master_id'] = master_id
        dst_dir = ctx.obj['PARAMS']['dir']

        for master in ctx.obj['PARAMS']['masters']:  # pylint: disable=E1136
            if int(master['idx']) == int(master_id):
                ctx.obj['PARAMS'].update({'me': master})

        run_sh = None
        if run:
            run_sh = os.path.join(dst_dir, 'treadmill', 'bin', 'run.sh')

        bootstrap.install(
            'zookeeper',
            dst_dir,
            ctx.obj['PARAMS'],
            run=run_sh
        )

    return zookeeper
