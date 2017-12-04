"""Admin Cell CLI module"""

import importlib
import logging
import sys
import time

import click
import jinja2
import ldap3
import yaml

from treadmill import admin
from treadmill import cli
from treadmill import context
from treadmill import master as master_api
from treadmill import zkadmin
from treadmill import zknamespace as z
from treadmill import zkutils
from treadmill.api import instance

_LOGGER = logging.getLogger(__name__)

_CELL_APIS = ['adminapi', 'wsapi', 'stateapi', 'cellapi']


class CellCtx(object):
    """Cell context."""

    def __init__(self):
        self.cell = context.GLOBAL.cell

        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(self.cell)
        self.version = cell['version']

        self.proid = cell['username']
        self.treadmill = cell.get('root')
        if not self.treadmill:
            self.treadmill = _treadmill_root(self.version)


def _treadmill_root(version):
    """Load cell version plugin"""
    cell_plugin = importlib.import_module('treadmill.plugins.cell_model')
    return cell_plugin.treadmill_root(version)


def _cell_version(cellname):
    """Gets the cell based treadmill root."""
    admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
    cell = admin_cell.get(cellname)
    version = cell.get('version')

    if version is None:
        raise Exception('Version is not defined for cell: %s')

    root = cell.get('root')
    if not root:
        root = _treadmill_root(version)

    return version, root


def _zkok(cell):
    """Check that Zookeeper ensemble has two followers and is ok."""
    status = {
        'follower': 0,
        'leader': 0,
    }

    for master in cell['masters']:
        hostname = master['hostname']
        port = master['zk-client-port']
        try:
            zk_status = zkadmin.netcat(hostname, port, 'stat\n')
            for line in zk_status.splitlines():
                line.strip()
                if line == 'Mode: follower':
                    status['follower'] += 1
                    break
                if line == 'Mode: leader':
                    status['leader'] += 1
                    break
        except Exception:
            return False

    return (status['leader'] == 1) and (status['follower'] == 2)


def init():
    """Admin Cell CLI module"""

    @click.group(name='cell')
    @click.option('--cell', required=True,
                  envvar='TREADMILL_CELL',
                  is_eager=True, callback=cli.handle_context_opt,
                  expose_value=False)
    @click.pass_context
    def cell_grp(ctx):
        """Manage treadmill cell."""
        ctx.obj = CellCtx()

    @cell_grp.command(name='clear-blackout')
    def clear_blackout():
        """Clear cell blackout."""
        zkclient = context.GLOBAL.zk.conn

        blacked_out = zkclient.get_children(z.BLACKEDOUT_SERVERS)
        for server in blacked_out:
            zkutils.ensure_deleted(zkclient, z.path.blackedout_server(server))

    @cell_grp.command(name='configure-apps')
    @click.option('--root', help='Treadmill root override.')
    @click.option('--apps', type=cli.LIST, help='List of apps to configure.')
    @click.option('--dry-run', help='Dry run.', is_flag=True, default=False)
    @click.pass_context
    def configure_apps(ctx, root, apps, dry_run):
        """Configure cell API."""
        admin_app = admin.Application(context.GLOBAL.ldap.conn)

        if not apps:
            apps = _CELL_APIS

        if root:
            ctx.obj.treadmill = root

        jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))
        for appname in apps:
            template = jinja_env.get_template(appname)
            app = yaml.load(template.render(**ctx.obj.__dict__))

            fullname = '%s.%s.%s' % (ctx.obj.proid, appname, ctx.obj.cell)

            _LOGGER.debug(fullname)
            _LOGGER.debug(yaml.dump(app))

            if not dry_run:
                try:
                    admin_app.create(fullname, app)
                except ldap3.LDAPEntryAlreadyExistsResult:
                    admin_app.replace(fullname, app)

    @cell_grp.command(name='configure-monitors')
    @click.option('--monitors', type=cli.DICT,
                  help='Key/value pairs for monitor count overrides.')
    @click.pass_context
    def configure_monitors(ctx, monitors):
        """Configure system apps monitors."""
        jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))

        if not monitors:
            template = jinja_env.get_template('monitors')
            monitors = yaml.load(template.render(**ctx.obj.__dict__))

        for name, count in monitors.items():
            _LOGGER.debug('%s %s', name, count)
            master_api.update_appmonitor(
                context.GLOBAL.zk.conn,
                name,
                count
            )

    @cell_grp.command(name='configure-appgroups')
    @click.pass_context
    def configure_appgroups(ctx):
        """Configure system app groups."""
        jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))

        template = jinja_env.get_template('appgroups')
        appgroups = yaml.load(template.render(**ctx.obj.__dict__))

        admin_app_group = admin.AppGroup(context.GLOBAL.ldap.conn)
        for name, data in appgroups.items():
            _LOGGER.debug('%s %s', name, data)
            try:
                admin_app_group.create(name, data)
            except ldap3.LDAPEntryAlreadyExistsResult:
                admin_app_group.update(name, data)

            existing = admin_app_group.get(name)
            group_cells = set(existing['cells'])
            group_cells.update([ctx.obj.cell])
            admin_app_group.update(name, {'cells': list(group_cells)})
            existing = admin_app_group.get(name)
            _LOGGER.debug(existing)

    @cell_grp.command(name='restart-apps')
    @click.option('--apps', type=cli.LIST,
                  help='List of apps to restart.')
    @click.option('--wait', type=int, help='Interval to wait before restart.',
                  default=20)
    @click.pass_context
    def restart_apps(ctx, wait, apps):
        """Restart cell API."""
        jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))

        instance_api = instance.init(None)
        template = jinja_env.get_template('monitors')
        monitors = yaml.load(template.render(**ctx.obj.__dict__))

        for name, count in monitors.items():
            _, appname, _ = name.split('.')
            if apps and appname not in apps:
                continue

            for _idx in range(0, count):
                instance_id = instance_api.create(name, {}, 1)
                print(list(map(str, instance_id)), end='')
                for _sec in range(0, wait):
                    print('.', end='')
                    sys.stdout.flush()
                    time.sleep(1)
                print('.')

    del clear_blackout
    del restart_apps
    del configure_apps
    del configure_monitors
    del configure_appgroups

    return cell_grp
