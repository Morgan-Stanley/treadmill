"""Manages Treadmill applications lifecycle.
"""

import json
import logging
import os
import shutil
import tempfile

import treadmill
from treadmill import appcfg
from treadmill import appevents
from treadmill import supervisor
from treadmill import utils

from treadmill.appcfg import manifest as app_manifest
from treadmill.apptrace import events

_LOGGER = logging.getLogger(__name__)


def configure(tm_env, event, runtime):
    """Creates directory necessary for starting the application.

    This operation is idem-potent (it can be repeated).

    The directory layout is::

        - (treadmill root)/
          - apps/
            - (app unique name)/
              - data/
                - app_start
                - app.json
                - manifest.yml
                - policy.json
                env/
                - TREADMILL_*
                run
                finish
                log/
                - run

    The 'run' script is responsible for creating container environment
     and starting the container.

    The 'finish' script is invoked when container terminates and will
    deallocate any resources (NAT rules, etc) that were allocated for the
    container.
    """
    # Load the app from the event
    try:
        manifest_data = app_manifest.load(tm_env, event, runtime)
    except IOError:
        # File is gone. Nothing to do.
        _LOGGER.exception("No event to load: %r", event)
        return

    # Freeze the app data into a namedtuple object
    app = utils.to_obj(manifest_data)

    # Generate a unique name for the app
    uniq_name = appcfg.app_unique_name(app)

    # Write the actual container start script
    run_script = ' '.join([
        'exec', treadmill.TREADMILL_BIN,
        'sproc', 'run', '.'
    ])

    # Create the service for that container
    container_svc = supervisor.create_service(
        tm_env.apps_dir,
        name=uniq_name,
        app_run_script=run_script,
        downed=True,
        monitor_policy={'limit': 0, 'interval': 60},
        userid='root',
        environ={},
        environment=app.environment
    )
    data_dir = container_svc.data_dir

    # Copy the original event as 'manifest.yml' in the container dir
    shutil.copyfile(
        event,
        os.path.join(data_dir, 'manifest.yml')
    )

    # Store the app.json in the container directory
    app_json = os.path.join(data_dir, appcfg.APP_JSON)
    with open(app_json, 'w') as f:
        json.dump(manifest_data, f)

    appevents.post(
        tm_env.app_events_dir,
        events.ConfiguredTraceEvent(
            instanceid=app.name,
            uniqueid=app.uniqueid
        )
    )

    return container_svc.directory


def schedule(container_dir, running_link):
    """Kick start the container by placing it in the running folder.
    """
    # NOTE: We use a temporary file + rename behavior to override any
    #       potential old symlinks.
    tmpfile = tempfile.mktemp(prefix='.tmp',
                              dir=os.path.dirname(running_link))
    os.symlink(container_dir, tmpfile)
    os.rename(tmpfile, running_link)
