# Copyright 2016 Red Hat Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module provides multiple classes representing Brew entities, mostly
used to issue testing (scratch) builds and evaluating results of such
requests.
"""

import os.path
import logging
import subprocess
import tempfile
import platform_ci.notifications as notifications


class BuildToCommitterMapping(object):
    """Provides a simple way to store committer addresses for CI-issued builds.

    When CI issues Brew builds automatically, it does so under its own machine
    credentials, not under credentials of the person who actually performed the
    action that triggered the CI action (usually a git push). Therefore, Brew
    tracks the CI machine account as a Brew build issuer, which may cause
    later notifications (e.g. when such build is tested later) to be sent to
    the machine account address instead of the right recipient.

    This class allows to store committer information at the time when the build
    is issued, mapping the issued build task ID to this committer information,
    so it can be retrieved later.

    Currently, the class stores the mapping in the filesystem, so it relies on
    the later processing happening on the same Jenkins slave. This is fragile
    and should be improved.
    """
    @staticmethod
    def get_mapping_file_path(task_id):
        """Return a filesystem path to a mapping file for a given Task ID."""
        tempdir = tempfile.gettempdir()
        task_id_filename = "platform-ci-{0}.mapping".format(task_id)
        return os.path.join(tempdir, task_id_filename)

    def __init__(self, task_id, committer):
        self.task_id = task_id
        self.committer = committer

    def save(self):
        """Save the mapping to the filesystem."""
        with open(BuildToCommitterMapping.get_mapping_file_path(self.task_id), "w") as mapping_file:
            mapping_file.write(self.committer)


# pylint: disable=too-few-public-methods
class BrewBuildAttemptException(notifications.PlatformCIException):
    """Exception to be used on errors during Brew build attempts."""
    header = notifications.create_platform_error_header(notifications.HEADERS["BREW_BUILD"])


class BrewBuildAttempt(object):
    """Represents an attempt to build current DistGit branch in Brew.

    The build itself is issued using the 'rhpkg' command.
    """
    def __init__(self, target, logdir):
        self.target = target
        self._execution = None
        self.logfile_path = os.path.join(logdir, "build-%s.log" % self.target)
        self._logfile = None
        self._success = None

    def execute(self):
        """Issue the request to build a scratch build in Brew.

        The method returns immediately after the request is issued, it does not
        wait until the request is finished.

        The current working directory needs to contain a checked-out DistGit
        branch.
        """
        logging.info("Building for target [%s]", self.target)
        self._logfile = open(self.logfile_path, "w")
        self._execution = subprocess.Popen(["rhpkg", "build", "--scratch", "--skip-nvr-check", "--target", self.target],
                                           stdout=self._logfile, stderr=self._logfile)

    def wait(self):
        """Blocks until the build request is finished.

        After this methods returns, the result is available to be picked up
        by the passed() method and the logs are created.
        """
        self._execution.wait()
        if self._execution.returncode == 0:
            logging.info("Brew build for target [%s] was successful", self.target)
            self._success = True
        else:
            logging.error("Brew build for target [%s] failed", self.target)
            self._success = False
        self._logfile.close()

    def passed(self):
        """Returns True if the build request was successful, False otherwise.

        Can be only called after a previous wait() method call.
        Raises:
            BrewBuildAttemptException: When called without previous wait() method
                call.
        """
        if self._success is None:
            raise BrewBuildAttemptException("Brew build success was not set in wait() method")

        return self._success

    @property
    def short_result(self):
        """Returns "PASS" if build request was successful, "FAIL" otherwise.

        Can be only called after a previous wait() method call.

        Raises:
            BrewBuildAttemptException: When called without previous wait() method
                call.
        """
        if self.passed():
            return "PASS"
        else:
            return "FAIL"

    @property
    def url(self):
        """Returns a URL to the Brew task of an issued task.

        Can be only called after a previous wait() method call.
        """
        with open(self.logfile_path, "r") as logfile:
            for line in logfile:
                if line.startswith("Task info: "):
                    return line[11:].strip()
        return None

    @property
    def task_id(self):
        """Returns a Task ID of an issued task.

        Can be only called after a previous wait() method call.
        """
        with open(self.logfile_path, "r") as logfile:
            for line in logfile:
                if line.startswith("Created task: "):
                    return line[14:].strip()
        return None


class BrewBuildAttempts(object):
    """Represents multiple simultaneous build attempts."""

    def __init__(self, targets, logdir):
        self.targets = targets
        self.logdir = logdir
        self.builds = {}

    def all(self):
        """Returns a list of all build requests."""
        return self.builds.values()

    def execute(self):
        """Issue all build requests.

        The method returns immediately after all requests are issued, it does
        not wait until any request is finished.
        """
        for target in self.targets:
            self.builds[target] = BrewBuildAttempt(target, self.logdir)
            self.builds[target].execute()

    def wait(self):
        """Block until all issued build requests finish.

        After this methods returns, the results are available to be collected.
        """
        for target in self.targets:
            self.builds[target].wait()

    def all_successful(self):
        """Returns all successful build requests.

        Can be only called after a previous wait() method call.
        """
        for target in self.targets:
            if not self.builds[target].passed():
                return False

        return True

    def count_failed(self):
        """Returns how many build attempts were not successful.

        Can be only called after a previous wait() method call.
        """
        failed = 0
        for target in self.builds:
            if not self.builds[target].passed():
                failed += 1
        return failed
