"""Syncronizes Zookeeper to file system.
"""

import logging
import glob
import os
import tempfile
import time
import kazoo

from treadmill import fs
from treadmill import exc
from treadmill import utils
from treadmill import zknamespace as z
from treadmill import zkutils


_LOGGER = logging.getLogger(__name__)


def write_data(fpath, data, modified, raise_err=True):
    """Safely write data to file path."""
    with tempfile.NamedTemporaryFile(dir=os.path.dirname(fpath),
                                     delete=False,
                                     prefix='.tmp',
                                     mode='w') as temp:
        if data:
            temp.write(data)
        os.fchmod(temp.fileno(), 0o644)
    os.utime(temp.name, (modified, modified))
    try:
        os.rename(temp.name, fpath)
    except OSError:
        _LOGGER.error('Unable to rename: %s => %s', temp.name, fpath,
                      exc_info=True)
        if raise_err:
            raise


class Zk2Fs(object):
    """Syncronize Zookeeper with file system."""

    def __init__(self, zkclient, fsroot):
        self.watches = set()
        self.processed_once = set()
        self.zkclient = zkclient
        self.fsroot = fsroot
        self.ready = False

        self.zkclient.add_listener(zkutils.exit_on_lost)

    def mark_ready(self):
        """Mark itself as ready, typically past initial sync."""
        self.ready = True
        self._update_last()

    def _update_last(self):
        """Update .modified timestamp to indicate changes were made."""
        if self.ready:
            modified_file = os.path.join(self.fsroot, '.modified')
            utils.touch(modified_file)
            os.utime(modified_file, (time.time(), time.time()))

    def _default_on_del(self, zkpath):
        """Default callback invoked on node delete, remove file."""
        fs.rm_safe(self.fpath(zkpath))

    def _default_on_add(self, zknode):
        """Default callback invoked on node is added, default - sync data."""
        self.sync_data(zknode)

    def _write_data(self, fpath, data, stat):
        """Write Zookeeper data to filesystem.
        """
        write_data(fpath, data, stat.last_modified, raise_err=True)

    def _data_watch(self, zkpath, data, stat, event):
        """Invoked when data changes."""
        fpath = self.fpath(zkpath)
        if data is None and event is None:
            _LOGGER.info('Node does not exist: %s', zkpath)
            self.watches.discard(zkpath)
            fs.rm_safe(fpath)

        elif event is not None and event.type == 'DELETED':
            _LOGGER.info('Node removed: %s', zkpath)
            self.watches.discard(zkpath)
            fs.rm_safe(fpath)
        else:
            self._write_data(fpath, data, stat)

        # Returning False will not renew the watch.
        renew = zkpath in self.watches
        _LOGGER.info('Renew watch on %s - %s', zkpath, renew)
        return renew

    def _filter_children_actions(self, sorted_children, sorted_filenames, add,
                                 remove, common):
        """sorts the children actions to add, remove and common."""
        num_children = len(sorted_children)
        num_filenames = len(sorted_filenames)

        child_idx = 0
        file_idx = 0

        while child_idx < num_children or file_idx < num_filenames:
            child_name = None
            if child_idx < num_children:
                child_name = sorted_children[child_idx]

            file_name = None
            if file_idx < num_filenames:
                file_name = sorted_filenames[file_idx]

            if child_name is None:
                remove.append(file_name)
                file_idx += 1

            elif file_name is None:
                add.append(child_name)
                child_idx += 1

            elif child_name == file_name:
                common.append(child_name)
                child_idx += 1
                file_idx += 1

            elif child_name < file_name:
                add.append(child_name)
                child_idx += 1

            else:
                remove.append(file_name)
                file_idx += 1

    def _children_watch(self, zkpath, children, watch_data,
                        on_add, on_del, cont_watch_predicate=None):
        """Callback invoked on children watch."""
        fpath = self.fpath(zkpath)

        sorted_children = sorted(children)
        sorted_filenames = sorted(map(os.path.basename,
                                      glob.glob(os.path.join(fpath, '*'))))

        add = []
        remove = []
        common = []

        self._filter_children_actions(sorted_children, sorted_filenames,
                                      add, remove, common)

        for node in remove:
            _LOGGER.info('Delete: %s', node)
            zknode = z.join_zookeeper_path(zkpath, node)
            self.watches.discard(zknode)
            on_del(zknode)

        if zkpath not in self.processed_once:
            self.processed_once.add(zkpath)
            for node in common:
                _LOGGER.info('Common: %s', node)

                zknode = z.join_zookeeper_path(zkpath, node)
                if watch_data:
                    self.watches.add(zknode)

                on_add(zknode)

        for node in add:
            _LOGGER.info('Add: %s', node)

            zknode = z.join_zookeeper_path(zkpath, node)
            if watch_data:
                self.watches.add(zknode)

            on_add(zknode)

        if cont_watch_predicate:
            return cont_watch_predicate(zkpath, sorted_children)

        return True

    def fpath(self, zkpath):
        """Returns file path to given zk node."""
        return os.path.join(self.fsroot, zkpath.lstrip('/'))

    def sync_data(self, zkpath):
        """Sync zk node data to file."""

        if zkpath in self.watches:
            @self.zkclient.DataWatch(zkpath)
            @exc.exit_on_unhandled
            def _data_watch(data, stat, event):
                """Invoked when data changes."""
                renew = self._data_watch(zkpath, data, stat, event)
                self._update_last()
                return renew

        else:
            fpath = self.fpath(zkpath)
            data, stat = self.zkclient.get(zkpath)
            self._write_data(fpath, data, stat)
            self._update_last()

    def _make_children_watch(self, zkpath, watch_data=False,
                             on_add=None, on_del=None,
                             cont_watch_predicate=None):
        """Make children watch function."""

        _LOGGER.debug('Establish children watch on: %s', zkpath)

        @self.zkclient.ChildrenWatch(zkpath)
        @exc.exit_on_unhandled
        def _children_watch(children):
            """Callback invoked on children watch."""
            renew = self._children_watch(
                zkpath,
                children,
                watch_data,
                on_add,
                on_del,
                cont_watch_predicate=cont_watch_predicate,
            )

            self._update_last()
            return renew

    def sync_children(self, zkpath, watch_data=False,
                      on_add=None, on_del=None,
                      need_watch_predicate=None,
                      cont_watch_predicate=None):
        """Sync children of zkpath to fpath.

        need_watch_predicate decides if the watch is needed based on the
        zkpath alone.

        cont_watch_prediacate decides if the watch is needed based on content
        of zkpath children.

        To avoid race condition, both need to return False, if one of them
        returns True, watch will be set.
        """

        _LOGGER.info('sync children: zk = %s, watch_data: %s',
                     zkpath,
                     watch_data)

        fpath = self.fpath(zkpath)
        fs.mkdir_safe(fpath)

        done_file = os.path.join(fpath, '.done')
        if os.path.exists(done_file):
            _LOGGER.info('Found done file: %s, nothing to watch.', done_file)
            return

        if not on_del:
            on_del = self._default_on_del
        if not on_add:
            on_add = self._default_on_add

        need_watch = True
        if need_watch_predicate:
            need_watch = need_watch_predicate(zkpath)
            _LOGGER.info('Need watch on %s: %s', zkpath, need_watch)

        if need_watch:
            self._make_children_watch(
                zkpath, watch_data, on_add, on_del,
                cont_watch_predicate=cont_watch_predicate
            )
        else:
            try:
                children = self.zkclient.get_children(zkpath)
            except kazoo.client.NoNodeError:
                children = []

            need_watch = self._children_watch(
                zkpath,
                children,
                watch_data,
                on_add,
                on_del,
                cont_watch_predicate=cont_watch_predicate,
            )

            if need_watch:
                self._make_children_watch(
                    zkpath, watch_data, on_add, on_del,
                    cont_watch_predicate=cont_watch_predicate
                )

            self._update_last()

        if not need_watch:
            utils.touch(done_file)
