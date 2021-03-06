# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import sys


def get_os():
    "Human-friendly OS name"
    if sys.platform.find('freebsd') != -1:
        return 'freebsd'
    elif sys.platform.find('linux') != -1:
        return 'linux'
    elif sys.platform.find('sunos') != -1:
        return 'solaris'
    # TODO: add AIX
    else:
        return sys.platform


class Platform(object):
    """
    Return information about the given platform.
    """
    @staticmethod
    def is_freebsd():
        return sys.platform.startswith("freebsd")

    @staticmethod
    def is_linux():
        return 'linux' in sys.platform

    @staticmethod
    def is_solaris():
        return sys.platform == "sunos5"
