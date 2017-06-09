"""Treadmill admin cron CLI tools.
"""

import logging

import click
import pytz

from apscheduler.jobstores import base

from treadmill import cli
from treadmill import context
from treadmill import cron
from treadmill import exc

from treadmill.api import cron as cron_api

_LOGGER = logging.getLogger(__name__)

_FORMATTER = cli.make_formatter(cli.CronPrettyFormatter)

ON_EXCEPTIONS = cli.handle_exceptions([
    (exc.InvalidInputError, None),
    (base.JobLookupError, None),
    (pytz.UnknownTimeZoneError, 'Unknown timezone'),
])


def init():
    """Return top level command handler."""
    ctx = {}

    @click.group()
    @click.option('--cell', required=True,
                  envvar='TREADMILL_CELL',
                  callback=cli.handle_context_opt,
                  expose_value=False)
    def cron_group():
        """Manage Treadmill cron jobs"""
        zkclient = context.GLOBAL.zk.conn
        ctx['scheduler'] = cron.get_scheduler(zkclient)

    @cron_group.command()
    @click.argument('job_id')
    @click.argument('event',
                    type=click.Choice([
                        'app:start', 'app:stop', 'monitor:set-count'
                    ]))
    @click.option('--resource',
                  help='The resource to schedule, e.g. an app name',
                  required=True)
    @click.option('--expression', help='The cron expression for scheduling',
                  required=True)
    @click.option('--count', help='The number of instances to start',
                  type=int)
    @ON_EXCEPTIONS
    def configure(job_id, event, resource, expression, count):
        """Create or modify an existing app start schedule"""
        scheduler = ctx['scheduler']

        job = cron_api.update_job(
            scheduler, job_id, event, resource, expression, count
        )

        cli.out(_FORMATTER(cron.job_to_dict(job)))

    @cron_group.command(name='list')
    def _list():
        """List out all cron events"""
        scheduler = ctx['scheduler']

        jobs = scheduler.get_jobs()

        job_dicts = [cron.job_to_dict(job) for job in jobs]
        _LOGGER.debug('job_dicts: %r', jobs)

        cli.out(_FORMATTER(job_dicts))

    @cron_group.command()
    @click.argument('job_id')
    @ON_EXCEPTIONS
    def delete(job_id):
        """Delete an app schedule"""
        scheduler = ctx['scheduler']

        _LOGGER.info('Removing job %s', job_id)
        scheduler.remove_job(job_id)

    del configure
    del _list
    del delete

    return cron_group
