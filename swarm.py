# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2016 Bitcraze AB
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
from threading import Thread

from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import traceback

class _Factory:
    """
    Default Crazyflie factory class.
    """

    def construct(self, uri):
        return SyncCrazyflie(uri)


class CachedCfFactory:
    """
    Factory class that creates Crazyflie instances with TOC caching
    to reduce connection time.
    """

    def __init__(self, ro_cache=None, rw_cache=None):
        self.ro_cache = ro_cache
        self.rw_cache = rw_cache

    def construct(self, uri):
        cf = Crazyflie(ro_cache=self.ro_cache, rw_cache=self.rw_cache)
        return SyncCrazyflie(uri, cf=cf)


class Swarm:

    def __init__(self, uris, factory=_Factory()):

        self._cfs = {}
        self._is_open = False

        for uri in uris:
            self._cfs[uri] = factory.construct(uri)

    def open_links(self):
        """
        Open links to all individuals in the swarm
        """
        if self._is_open:
            raise Exception('Already opened')

        try:
            self.parallel_safe(lambda scf: scf.open_link())
            self._is_open = True
        except Exception as e:
            self.close_links()
            raise e

    def close_links(self):
        """
        Close all open links
        """
        for uri, cf in self._cfs.items():
            cf.close_link()

        self._is_open = False

    def __enter__(self):
        self.open_links()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_links()

    def sequential(self, func, args_dict=None):
 
        for uri, cf in self._cfs.items():
            args = self._process_args_dict(cf, uri, args_dict)
            func(*args)

    def parallel(self, func, args_dict=None):

        try:
            self.parallel_safe(func, args_dict)
        except Exception:
            print("parallel exception")
            print(traceback.format_exc())
            pass

    def parallel_safe(self, func, args_dict=None):

        threads = []
        reporter = self.Reporter()

        for uri, scf in self._cfs.items():
            args = [func, reporter] + \
                self._process_args_dict(scf, uri, args_dict)

            thread = Thread(target=self._thread_function_wrapper, args=args)
            threads.append(thread)
            thread.start()

        #for thread in threads:
        #    thread.join()

        if reporter.is_error_reported():
            first_error = reporter.errors[0]
            raise Exception('One or more threads raised an exception when '
                            'executing parallel task') from first_error

    def _thread_function_wrapper(self, *args):
        reporter = None
        try:
            func = args[0]
            reporter = args[1]
            func(*args[2:])
        except Exception as e:
            if reporter:
                reporter.report_error(e)

    def _process_args_dict(self, scf, uri, args_dict):
        args = [scf]

        if args_dict:
            args += args_dict[uri]

        return args

    class Reporter:
        def __init__(self):
            self.error_reported = False
            self._errors = []

        @property
        def errors(self):
            return self._errors

        def report_error(self, e):
            self.error_reported = True
            self._errors.append(e)

        def is_error_reported(self):
            return self.error_reported

