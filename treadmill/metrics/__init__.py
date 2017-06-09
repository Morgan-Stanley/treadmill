"""Collects and reports container and host metrics.
"""

import errno
import logging
import os
import time

from treadmill import cgroups
from treadmill import cgutils
from treadmill import psmem

NANOSECS_PER_10MILLI = 10000000

_LOGGER = logging.getLogger(__name__)

# Patterns to match Treadmill core processes, to use as filter in psmem.
#
# TODO: currently unused.
_SYSPROCS = ['s6-*', 'treadmill_disc*', 'pid1', 'app_tickets', 'app_presence',
             'app_endpoint*']

# yield metrics in chunks of 100
_METRICS_CHUNK_SIZE = 100


def read_memory_stats(cgrp):
    """Reads memory stats for the given treadmill app or system service.

    Returns dict: key is pseudofile name
    """
    metric = cgrp_meminfo(cgrp)
    stats = cgutils.get_stat('memory', cgrp)
    metric['memory.stats'] = stats

    return metric


_MEMORY_TYPE = [
    'memory.failcnt',
    'memory.limit_in_bytes',
    'memory.max_usage_in_bytes',
    'memory.memsw.failcnt',
    'memory.memsw.limit_in_bytes',
    'memory.memsw.max_usage_in_bytes',
    'memory.memsw.usage_in_bytes',
    'memory.soft_limit_in_bytes',
    'memory.usage_in_bytes',
]


def cgrp_meminfo(cgrp, *pseudofiles):
    """Grab the cgrp mem limits"""

    if pseudofiles is None or len(pseudofiles) == 0:
        pseudofiles = _MEMORY_TYPE

    metrics = {}
    for pseudofile in pseudofiles:
        data = cgroups.get_value('memory', cgrp, pseudofile)

        # remove memory. prefix
        metrics[pseudofile] = data

    return metrics


def read_psmem_stats(appname, allpids):
    """Reads per-proc memory details stats."""
    cgrp = os.path.join('treadmill/apps', appname)
    group_pids = set(cgutils.pids_in_cgroup('memory', cgrp))

    # Intersection of all /proc pids (allpids) and pid in .../tasks will give
    # the set we are interested in.
    #
    # "tasks" contain thread pids that we want to filter out.
    meminfo = psmem.get_memory_usage(allpids & group_pids, use_pss=True)
    return meminfo


_BLKIO_INFO_TYPE = [
    'blkio.throttle.io_service_bytes',
    'blkio.throttle.io_serviced',
    'blkio.io_service_bytes',
    'blkio.io_serviced',
    'blkio.io_merged',
    'blkio.io_queued',
]


def read_blkio_info_stats(cgrp, *pseudofiles):
    """Read bklio statistics for the given Treadmill app.
    """
    if pseudofiles is None or len(pseudofiles) == 0:
        pseudofiles = _BLKIO_INFO_TYPE

    metrics = {}
    for pseudofile in pseudofiles:
        blkio_info = cgutils.get_blkio_info(cgrp, pseudofile)

        metrics[pseudofile] = blkio_info

    return metrics


_BLKIO_VALUE_TYPE = [
    'blkio.sectors',
    'blkio.time',
]


def read_blkio_value_stats(cgrp, *pseudofiles):
    """ read blkio value based cgroup pseudofiles
    """
    if pseudofiles is None or len(pseudofiles) == 0:
        pseudofiles = _BLKIO_VALUE_TYPE

    metrics = {}
    for pseudofile in pseudofiles:
        blkio_info = cgutils.get_blkio_value(cgrp, pseudofile)

        metrics[pseudofile] = blkio_info

    return metrics


def read_load():
    """Reads server load stats."""
    with open('/proc/loadavg') as f:
        # /proc/loadavg file format:
        # 1min_avg 5min_avg 15min_avg ...
        line = f.read()
        loadavg_1min = line.split()[0]
        loadavg_5min = line.split()[1]

        return (loadavg_1min, loadavg_5min)


def read_cpuacct_stat(cgrp):
    """read cpuacct.stat pseudo file
    """
    divided_usage = cgutils.get_stat('cpuacct', cgrp)
    # usage in other file in nanseconds, in cpuaaac.stat is 10 miliseconds
    for name, value in divided_usage.items():
        divided_usage[name] = value * NANOSECS_PER_10MILLI

    return divided_usage


def read_cpu_stat(cgrp):
    """read cpu.stat pseudo file
    """
    throttled_usage = cgutils.get_stat('cpu', cgrp)
    return throttled_usage


def read_cpu_system_usage():
    """ read cpu system usage
    """
    # read /proc/stat
    pass


def read_cpu_stats(cgrp):
    """Calculate normalized CPU stats given cgroup name.

    Returns dict: key is pseudofile name
    """
    data = {}
    data['cpuacct.usage_percpu'] = cgutils.per_cpu_usage(cgrp)
    data['cpuacct.usage'] = cgutils.cpu_usage(cgrp)
    data['cpuacct.stat'] = read_cpuacct_stat(cgrp)
    data['cpu.stat'] = read_cpu_stat(cgrp)

    return data


def app_metrics(cgrp):
    """Returns app metrics or empty dict if app not found."""
    result = {}

    try:
        result['timestamp'] = time.time()

        # merge memory stats into dict
        memory_stats = read_memory_stats(cgrp)
        result.update(memory_stats)

        # merge cpu stats into dict
        cpu_stats = read_cpu_stats(cgrp)
        result.update(cpu_stats)

        # merge blkio stats into dict
        blkio_stats = read_blkio_info_stats(cgrp)
        result.update(blkio_stats)
        blkio_stats = read_blkio_value_stats(cgrp)
        result.update(blkio_stats)

    except IOError as err:
        if err.errno != errno.ENOENT:
            raise err

    except OSError as err:
        if err.errno != errno.ENOENT:
            raise err

    return result
