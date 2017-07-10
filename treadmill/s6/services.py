"""S6 services management.
"""

import abc
import errno
import logging
import os
import sys

import enum
import six

from treadmill import fs
from ._utils import (
    data_read,
    data_write,
    environ_dir_read,
    environ_dir_write,
    script_read,
    script_write,
    set_list_read,
    set_list_write,
    value_read,
    value_write,
)

_LOGGER = logging.getLogger(__name__)


class ServiceType(enum.Enum):
    """Types of s6 services (per s6-rc definitions).
    """
    LongRun = 'longrun'
    Oneshot = 'oneshot'
    Bundle = 'bundle'


@six.add_metaclass(abc.ABCMeta)
class Service(object):
    """Abstract base class / factory of all s6 services.
    """
    __slots__ = (
        '_dir',
        '_name',
    )

    def __init__(self, directory, name):
        self._name = name
        self._dir = os.path.join(directory, name)

    def __repr__(self):
        return '{type}({name})'.format(
            type=self.__class__.__name__,
            name=self._name,
        )

    @abc.abstractproperty
    def type(self):
        """Type of the service.

        :returns ``ServiceType``:
            Type of the service.
        """
        pass

    @property
    def name(self):
        """Name of the service.

        :returns ``str``:
            Name of the service.
        """
        return self._name

    @property
    def directory(self):
        """Base filesystem directory of the service.

        :returns ``str``:
            Base directory of the service.
        """
        return self._dir

    @abc.abstractmethod
    def write(self):
        """Write down the service definition.
        """
        fs.mkdir_safe(self._dir)
        data_write(os.path.join(self._dir, 'type'), self.type.value)

    @classmethod
    def new(cls, svc_basedir, svc_name, svc_type, **kw_args):
        """Factory function instantiating a new service object from parameters.

        :param ``str`` svc_basedir:
            Base directory where to create the service.
        :param ``str`` svc_name:
            Name of the new service.
        :param ``ServiceType`` svc_type:
            Type for the new service.
        :param ``dict`` kw_args:
            Additional argument passed to the constructor of the new service.
        :returns ``Service``:
            New instance of the service
        """
        svc_mod = sys.modules[cls.__module__]
        svc_type = ServiceType(svc_type)
        svc_cls = getattr(svc_mod, svc_type.name.capitalize() + cls.__name__)
        if svc_cls is None:
            _LOGGER.critical('No implementation for service type %r', svc_type)
            svc_cls = cls

        return svc_cls(directory=svc_basedir,
                       name=svc_name,
                       **kw_args)

    @classmethod
    def from_dir(cls, directory):
        """Factory function instantiating a new service object from an existing
        directory.

        :param ``str`` directory:
            Directory where to read the service definition from.
        :returns ``Service``:
            New service instance or ``None`` if parsing failed.
        """
        try:
            svc_type = data_read(os.path.join(directory, 'type'))
        except IOError as err:
            if err.errno is errno.ENOENT:
                return None
            raise
        svc_basedir = os.path.dirname(directory)
        svc_name = os.path.basename(directory)
        return cls.new(svc_basedir=svc_basedir,
                       svc_name=svc_name,
                       svc_type=svc_type)


class BundleService(Service):
    """s6 rc bundle service.
    """
    __slots__ = (
        '_contents',
    )

    _TYPE = ServiceType.Bundle

    def __init__(self, directory, name, contents=None):
        super(BundleService, self).__init__(directory, name)
        self._contents = contents

    @property
    def type(self):
        return self._TYPE

    @property
    def _contents_file(self):
        return os.path.join(self._dir, 'contents')

    @property
    def contents(self):
        """Gets the contents of the bundle.
        """
        if self._contents is None:
            self._contents = set_list_read(self._contents_file)
        return self._contents

    def write(self):
        """Write down the service definition.
        """
        super(BundleService, self).write()
        # Mandatory settings
        if not self._contents and not os.path.exists(self._contents_file):
            raise ValueError('Invalid Bundle: No content')
        elif self._contents is not None:
            if not len(self._contents):
                raise ValueError('Invalid Bundle: empty')
            set_list_write(self._contents_file, self._contents)


@six.add_metaclass(abc.ABCMeta)
class _AtomicService(Service):
    """Abstract base class for all atomic services (per s6-rc definition).
    """
    __slots__ = (
        '_dependencies',
        '_timeout_up',
        '_timeout_down',
        '_env',
    )

    __metaclass__ = abc.ABCMeta

    def __init__(self, directory, name,
                 timeout_up=None, timeout_down=None,
                 dependencies=None, environ=None):
        super(_AtomicService, self).__init__(directory, name)
        self._dependencies = dependencies
        self._timeout_up = timeout_up
        self._timeout_down = timeout_down
        self._env = environ

    @property
    def data_dir(self):
        """Returns the data directory for the services.

        :returns ``str``:
            Full path to the service data directory.
        """
        return os.path.join(self._dir, 'data')

    @property
    def env_dir(self):
        """Returns the environ directory for the services.

        :returns ``str``:
            Full path to the service environ directory.
        """
        return os.path.join(self._dir, 'env')

    @property
    def environ(self):
        """Returns the environ dictionary for the services.

        :returns ``dict``:
            Service environ dictionary.
        """
        if self._env is None:
            self._env = environ_dir_read(self.env_dir)
        return self._env

    @environ.setter
    def environ(self, new_environ):
        self._env = new_environ

    @property
    def _dependencies_file(self):
        return os.path.join(self._dir, 'dependencies')

    @property
    def dependencies(self):
        """Returns the dependencies set for the services.

        :returns ``set``:
            Service dependencies set.
        """
        if self._dependencies is None:
            self._dependencies = set_list_read(self._dependencies_file)
        return self._dependencies

    @dependencies.setter
    def dependencies(self, new_deps):
        self._dependencies = set(new_deps)

    @property
    def timeout_up(self):
        """Returns amount of milliseconds to wait for the service to come up.

        :returns ``int``:
            Amount of milliseconds to wait. 0 means infinitely.
        """
        if self._timeout_up is None:
            self._timeout_up = value_read(
                os.path.join(self._dir, 'timeout-up'),
                default=0
            )
        return self._timeout_up

    @property
    def timeout_down(self):
        """Returns amount of milliseconds to wait for the service to come down.

        :returns ``int``:
            Amount of milliseconds to wait. 0 means infinitely.
        """
        if self._timeout_down is None:
            self._timeout_down = value_read(
                os.path.join(self._dir, 'timeout-down'),
                default=0
            )
        return self._timeout_down

    @abc.abstractmethod
    def write(self):
        """Write down the service definition.
        """
        super(_AtomicService, self).write()
        # We only write dependencies/environ if we have new ones.
        fs.mkdir_safe(self.env_dir)
        fs.mkdir_safe(self.data_dir)
        if self._dependencies is not None:
            set_list_write(self._dependencies_file, self._dependencies)
        if self._env is not None:
            environ_dir_write(self.env_dir, self._env)
        if self._timeout_up is not None:
            value_write(
                os.path.join(self._dir, 'timeout-up'),
                self._timeout_up
            )
        if self._timeout_down is not None:
            value_write(
                os.path.join(self._dir, 'timeout-down'),
                self._timeout_down
            )


class LongrunService(_AtomicService):
    """s6 long running service.
    """

    __slots__ = (
        '_consumer_for',
        '_default_down',
        '_finish_script',
        '_log_run_script',
        '_notification_fd',
        '_pipeline_name',
        '_producer_for',
        '_run_script',
        '_timeout_finish',
    )

    _TYPE = ServiceType.LongRun

    def __init__(self, directory, name,
                 run_script=None, finish_script=None, notification_fd=None,
                 log_run_script=None, timeout_finish=None, default_down=None,
                 pipeline_name=None, producer_for=None, consumer_for=None,
                 dependencies=None, environ=None):
        super(LongrunService, self).__init__(
            directory,
            name,
            dependencies=dependencies,
            environ=environ
        )
        if producer_for and log_run_script:
            raise ValueError('Invalid LongRun service options: producer/log')
        self._consumer_for = consumer_for
        self._default_down = default_down
        self._finish_script = finish_script
        self._log_run_script = log_run_script
        self._notification_fd = notification_fd
        self._pipeline_name = pipeline_name
        self._producer_for = producer_for
        self._run_script = run_script
        self._timeout_finish = timeout_finish

    @property
    def type(self):
        return self._TYPE

    @property
    def logger_dir(self):
        """Returns the logger directory for the services.

        :returns ``str``:
            Full path to the service log directory.
        """
        return os.path.join(self._dir, 'log')

    @property
    def notification_fd(self):
        """s6 "really up" notification fd.
        """
        if self._notification_fd is None:
            self._notification_fd = value_read(
                os.path.join(self._dir, 'notification-fd'),
                default=-1
            )
        return self._notification_fd

    @property
    def default_down(self):
        """Is the default service state set to down?
        """
        if self._default_down is None:
            self._default_down = os.path.exists(
                os.path.join(self._dir, 'down')
            )
        return self._default_down

    @default_down.setter
    def default_down(self, default_down):
        self._default_down = bool(default_down)

    @property
    def _run_file(self):
        return os.path.join(self._dir, 'run')

    @property
    def _finish_file(self):
        return os.path.join(self._dir, 'finish')

    @property
    def _log_run_file(self):
        return os.path.join(self.logger_dir, 'run')

    @property
    def run_script(self):
        """Service run script.
        """
        if self._run_script is None:
            self._run_script = script_read(self._run_file)
        return self._run_script

    @run_script.setter
    def run_script(self, new_script):
        self._run_script = new_script

    @property
    def finish_script(self):
        """Service finish script.
        """
        if self._finish_script is None:
            try:
                self._finish_script = script_read(self._finish_file)
            except IOError as err:
                if err.errno is not errno.ENOENT:
                    raise
        return self._finish_script

    @finish_script.setter
    def finish_script(self, new_script):
        self._finish_script = new_script

    @property
    def log_run_script(self):
        """Service log run script.
        """
        if self._log_run_script is None:
            try:
                self._log_run_script = script_read(self._log_run_file)
            except IOError as err:
                if err.errno is not errno.ENOENT:
                    raise
        return self._log_run_script

    @log_run_script.setter
    def log_run_script(self, new_script):
        self._log_run_script = new_script

    @property
    def timeout_finish(self):
        """Returns amount of milliseconds to wait for the finish script to
        complete.

        :returns ``int``:
            Amount of milliseconds to wait. 0 means infinitely. Default 5000.
        """
        # XXX: FIXME
        if self._timeout_finish is None:
            self._timeout_finish = value_read(
                os.path.join(self._dir, 'timeout-finish'),
                default=5000
            )
        return self._timeout_finish

    @property
    def _pipeline_name_file(self):
        return os.path.join(self._dir, 'pipeline-name')

    @property
    def pipeline_name(self):
        """Gets the name of the pipeline.
        """
        if self._pipeline_name is None:
            self._pipeline_name = data_read(self._pipeline_name_file)
        return self._pipeline_name

    @pipeline_name.setter
    def pipeline_name(self, new_name):
        self._pipeline_name = new_name

    @property
    def _producer_for_file(self):
        return os.path.join(self._dir, 'producer-for')

    @property
    def producer_for(self):
        """Gets which services this service is a producer for.
        """
        if self._producer_for is None:
            self._producer_for = data_read(self._producer_for_file)
        return self._producer_for

    @producer_for.setter
    def producer_for(self, new_name):
        """Sets the producer for another service.
        """
        self._producer_for = new_name

    @property
    def _consumer_for_file(self):
        return os.path.join(self._dir, 'consumer-for')

    @property
    def consumer_for(self):
        """Gets which services this service is a consumer for.
        """
        if self._consumer_for is None:
            self._consumer_for = data_read(self._consumer_for_file)
        return self._consumer_for

    @consumer_for.setter
    def consumer_for(self, new_name):
        """Sets which services this service is a consumer for.
        """
        self._consumer_for = new_name

    def write(self):
        """Write down the service definition.
        """
        # Disable R0912: Too many branche
        # pylint: disable=R0912
        super(LongrunService, self).write()
        # Mandatory settings
        if self._run_script is None and not os.path.exists(self._run_file):
            raise ValueError('Invalid LongRun service: not run script')
        elif self._run_script is not None:
            script_write(self._run_file, self._run_script)
            # Handle the case where the run script is a generator
            if not isinstance(self._run_script, str):
                self._run_script = None
        # Optional settings
        if self._finish_script is not None:
            script_write(self._finish_file, self._finish_script)
            # Handle the case where the finish script is a generator
            if not isinstance(self._finish_script, str):
                self._finish_script = None
        if self._log_run_script is not None:
            # Create the log dir on the spot
            fs.mkdir_safe(os.path.dirname(self._log_run_file))
            script_write(self._log_run_file, self._log_run_script)
            # Handle the case where the run script is a generator
            if not isinstance(self._log_run_script, str):
                self._log_run_script = None
        if self._default_down:
            data_write(
                os.path.join(self._dir, 'down'),
                None
            )
        else:
            fs.rm_safe(os.path.join(self._dir, 'down'))
        if self._timeout_finish is not None:
            value_write(
                os.path.join(self._dir, 'timeout-finish'),
                self._timeout_finish
            )
        if self._notification_fd is not None:
            value_write(
                os.path.join(self._dir, 'notification-fd'),
                self._notification_fd
            )
        if self._pipeline_name is not None:
            data_write(self._pipeline_name_file, self._pipeline_name)
        if self._producer_for is not None:
            data_write(self._producer_for_file, self._producer_for)
        if self._consumer_for is not None:
            data_write(self._consumer_for_file, self._consumer_for)


class OneshotService(_AtomicService):
    """Represents a s6 rc one-shot service which is only ever executed once.
    """
    __slots__ = (
        '_up',
        '_down',
    )
    # XXX timeout-up/timeout-down

    _TYPE = ServiceType.Oneshot

    def __init__(self, directory, name=None,
                 up_script=None, down_script=None,
                 dependencies=None, environ=None):
        super(OneshotService, self).__init__(
            directory,
            name,
            dependencies=dependencies,
            environ=environ
        )
        self._up = up_script
        self._down = down_script

    @property
    def type(self):
        return self._TYPE

    @property
    def _up_file(self):
        return os.path.join(self._dir, 'up')

    @property
    def _down_file(self):
        return os.path.join(self._dir, 'down')

    @property
    def up(self):
        """Gets the one shot service up file.
        """
        if self._up is None:
            self._up = script_read(self._up_file)
        return self._up

    @up.setter
    def up(self, new_script):
        """Sets the one-shot service up file.
        """
        self._up = new_script

    @property
    def down(self):
        """Gets the one-shot service down file.
        """
        if self._down is None:
            self._down = script_read(self._down_file)
        return self._down

    @down.setter
    def down(self, new_script):
        """Sets the one-shot service down file.
        """
        self._down = new_script

    def write(self):
        """Write down the service definition.
        """
        super(OneshotService, self).write()
        # Mandatory settings
        if not self._up and not os.path.exists(self._up_file):
            raise ValueError('Invalid Oneshot service: not up script')
        elif self._up is not None:
            script_write(self._up_file, self._up)
            if not isinstance(self._up_file, six.string_types):
                self._up_file = None
        # Optional settings
        if self._down is not None:
            script_write(self._down_file, self._down)
            if not isinstance(self._down_file, six.string_types):
                self._down_file = None


__all__ = (
    'Service',
    'BundleService',
    'LongrunService',
    'OneshotService'
)
