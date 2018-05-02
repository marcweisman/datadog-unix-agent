# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import errno
import inspect
import os

try:
    import psutil
except ImportError:
    psutil = None


def is_my_process(pid):
    """
    Check if the pid in the pid given corresponds to a running process
    and if psutil is available, check if it's process corresponding to
    the current executable
    """
    pid_existence = pid_exists(pid)

    if not psutil or not pid_existence:
        return pid_existence

    try:
        command = psutil.Process(pid).cmdline() or []
    except psutil.Error:
        # If we can't communicate with the process,
        # it's not an agent one
        return False
    # Check that the second arg contains (agent|dogstatsd).py
    # see http://stackoverflow.com/a/2345265
    exec_name = os.path.basename(inspect.stack()[-1][1]).lower()
    return len(command) > 1 and exec_name in command[1].lower()


def pid_exists(pid):
    """
    Check if a pid exists.
    Lighter than psutil.pid_exists
    """
    if psutil:
        return psutil.pid_exists(pid)

    # Code from psutil._psposix.pid_exists
    # See https://github.com/giampaolo/psutil/blob/master/psutil/_psposix.py
    if pid == 0:
        # According to "man 2 kill" PID 0 has a special meaning:
        # it refers to <<every process in the process group of the
        # calling process>> so we don't want to go any further.
        # If we get here it means this UNIX platform *does* have
        # a process with id 0.
        return True
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH) therefore we should never get
            # here. If we do let's be explicit in considering this
            # an error.
            raise err
    else:
        return True
