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

from sys import version_info
import unittest
import os.path
from mock import patch, Mock
# pylint: disable=no-name-in-module
from nose.tools import assert_raises

from .brew import BrewBuildAttempt, BrewBuildAttempts, BrewBuildAttemptException

# pylint: disable=no-member
try:
    major = version_info.major
except AttributeError:
    major = version_info[0]

# pylint: disable=import-error,wrong-import-order,wrong-import-position
if major == 2:
    import __builtin__ as builtins
else:
    import builtins


class BrewBuildAttemptTest(unittest.TestCase):
    TEST_TESTDIR = "/a/directory"
    TEST_TARGET = "rhel-6.88-candidate"

    def setUp(self):
        self.bba = BrewBuildAttempt(BrewBuildAttemptTest.TEST_TARGET, BrewBuildAttemptTest.TEST_TESTDIR)

    def sanity_test(self):
        assert self.bba.target == BrewBuildAttemptTest.TEST_TARGET
        assert self.bba.logfile_path == os.path.join(BrewBuildAttemptTest.TEST_TESTDIR, "build-rhel-6.88-candidate.log")
        assert_raises(BrewBuildAttemptException, self.bba.passed)

    @patch.object(builtins, 'open')
    @patch('subprocess.Popen')
    def execute_test(self, mock_popen, mock_open):
        self.bba.execute()
        assert mock_open.called
        assert mock_open.call_args[0][0] == self.bba.logfile_path
        assert mock_popen.called
        assert mock_popen.call_args[0][0] == ["rhpkg", "build", "--scratch", "--skip-nvr-check", "--target",
                                              BrewBuildAttemptTest.TEST_TARGET, "--arches", "x86_64"]

    # pylint: disable=protected-access
    def wait_success_test(self):
        self.bba._execution = Mock()
        self.bba._execution.wait = Mock()
        self.bba._execution.returncode = 0
        self.bba._logfile = Mock()
        self.bba._logfile.close = Mock()

        self.bba.wait()
        assert self.bba._execution.wait.called
        assert self.bba._logfile.close.called
        assert self.bba.passed()

    # pylint: disable=protected-access
    def wait_failure_test(self):
        self.bba._execution = Mock()
        self.bba._execution.wait = Mock()
        self.bba._execution.returncode = 1
        self.bba._logfile = Mock()
        self.bba._logfile.close = Mock()

        self.bba.wait()
        assert self.bba._execution.wait.called
        assert self.bba._logfile.close.called
        assert not self.bba.passed()


class BrewBuildAttemptsTest(unittest.TestCase):
    TEST_TARGETS = ("target-1-test", "target-2-test")
    TEST_LOGDIR = "/a/logdir"

    def setUp(self):
        self.bba = BrewBuildAttempts(BrewBuildAttemptsTest.TEST_TARGETS, BrewBuildAttemptsTest.TEST_LOGDIR)

    def sanity_test(self):
        assert self.bba.targets == BrewBuildAttemptsTest.TEST_TARGETS
        assert self.bba.logdir == BrewBuildAttemptsTest.TEST_LOGDIR
        assert self.bba.builds == {}

    @patch('platform_ci.brew.BrewBuildAttempt')
    def execute_test(self, mock_bba):
        mock_bba.return_value = Mock()
        mock_bba.return_value.execute = Mock()
        self.bba.execute()
        assert mock_bba.called
        assert mock_bba.call_count == 2
        assert len(self.bba.builds) == 2

        for target in BrewBuildAttemptsTest.TEST_TARGETS:
            assert self.bba.builds[target].execute.called

    def wait_test(self):
        for target in BrewBuildAttemptsTest.TEST_TARGETS:
            self.bba.builds[target] = Mock()
            self.bba.builds[target].wait = Mock()

        self.bba.wait()

        for target in BrewBuildAttemptsTest.TEST_TARGETS:
            assert self.bba.builds[target].wait.called

    def all_successful_test(self):
        for target in BrewBuildAttemptsTest.TEST_TARGETS:
            self.bba.builds[target] = Mock()
            self.bba.builds[target].passed = Mock()
            self.bba.builds[target].passed.return_value = True
        assert self.bba.all_successful()

        self.bba.builds[BrewBuildAttemptsTest.TEST_TARGETS[0]].passed.return_value = False
        assert not self.bba.all_successful()
