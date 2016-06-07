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
import tempfile
import os

from mock import MagicMock, patch
# pylint: disable=no-name-in-module
from nose.tools import assert_raises

from .jenkins import PlatformJenkins
from .jenkins_jobs import JobCommitDispatcher
import platform_ci.jenkins

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


# pylint: disable=too-many-public-methods
class PlatformJenkinsTest(unittest.TestCase):
    def setUp(self):
        self.template_dir = tempfile.mkdtemp()
        self.jenkins_mock = MagicMock()
        self.job_mock = MagicMock()
        self.url = "testing-url"

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        os.rmdir(self.template_dir)

    def get_jenkins_test(self):
        jenkins = PlatformJenkins.get_jenkins(self.url, self.template_dir)
        assert jenkins.jenkins_server is None
        assert jenkins.template_dir == self.template_dir
        assert jenkins.url == self.url


class PlatformJenkinsJavaCLITest(unittest.TestCase):
    def setUp(self):
        self.template_dir = tempfile.mkdtemp()
        self.job_mock = JobCommitDispatcher("component", "slave", "branch")
        self.jenkins = platform_ci.jenkins.PlatformJenkinsJavaCLI(self.template_dir, "url")
        self.job = MagicMock()
        self.job.name = "job_name"

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        os.rmdir(self.template_dir)

    @patch('subprocess.Popen')
    def view_exists_test(self, mock_popen):
        self.jenkins.view_exists("view")
        assert mock_popen.called
        command = mock_popen.call_args[0][0]
        assert command == (self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.GET_VIEW, "view"])

    @patch('subprocess.call')
    def enable_job_test(self, mock_call):
        mock_call.return_value = 0
        self.jenkins.enable_job(self.job_mock)
        assert mock_call.called
        command = mock_call.call_args[0][0]
        assert command == self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.ENABLE_JOB, self.job_mock.name]

        mock_call.reset_mock()
        mock_call.return_value = 1
        assert_raises(platform_ci.jenkins.PlatformJenkinsException, self.jenkins.enable_job, self.job)

    @patch.object(builtins, 'open')
    @patch('platform_ci.jenkins.PlatformJenkinsJavaCLI.view_exists')
    @patch('subprocess.Popen')
    def set_view_test(self, mock_popen, mock_view_exists, mock_open):
        # view exists -> testing view update
        mock_view_exists.return_value = True

        self.jenkins.set_view("view", "mock-file")
        assert mock_view_exists.called
        assert mock_popen.called
        command = mock_popen.call_args[0][0]
        assert command == (self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.UPDATE_VIEW, "view"])

        assert mock_open.called
        opened = mock_open.call_args[0][0]
        assert opened == "mock-file"

        mock_popen.reset_mock()
        mock_view_exists.reset_mock()

        # view does not exist -> testing view create
        mock_view_exists.return_value = False

        self.jenkins.set_view("view", "mock-file")
        assert mock_view_exists.called
        assert mock_popen.called
        command = mock_popen.call_args[0][0]
        print command
        assert command == (self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.CREATE_VIEW, "view"])

    @patch('subprocess.Popen')
    def job_exists_test(self, mock_popen):
        mock_popen_instance = MagicMock()
        mock_popen_instance.communicate = MagicMock()
        mock_popen_instance.communicate.return_value = ["job1\njob2"]

        mock_popen.return_value = mock_popen_instance

        self.job.name = "job1"
        assert self.jenkins.job_exists(self.job)
        self.job.name = "job3"
        assert not self.jenkins.job_exists(self.job)

        assert mock_popen.called
        command = mock_popen.call_args[0][0]
        assert command == (self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.LIST_JOBS])

    @patch('subprocess.call')
    def delete_job_test(self, mock_call):
        self.jenkins.delete_job(self.job)
        assert mock_call.called
        command = mock_call.call_args[0][0]
        assert command == (self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.DELETE_JOB, self.job.name])

    @patch('subprocess.call')
    def trigger_job_test(self, mock_call):
        mock_call.return_value = 0

        self.jenkins.trigger_job(self.job)
        assert mock_call.called
        command = mock_call.call_args[0][0]
        assert command == (self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.BUILD_JOB, self.job.name])

        mock_call.reset_mock()

        self.jenkins.trigger_job(self.job, {"param1": "param1-value", "param2": "param2-value"})
        assert mock_call.called
        command = mock_call.call_args[0][0]
        assert sorted(command) == sorted(self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.BUILD_JOB,
                                                             self.job.name, "-p", "param1=param1-value", "-p",
                                                             "param2=param2-value"])

        mock_call.return_value = 1
        assert_raises(platform_ci.jenkins.PlatformJenkinsException, self.jenkins.trigger_job, self.job)

    @patch('platform_ci.jjb.get_job_as_xml')
    @patch('subprocess.Popen')
    def create_job_test(self, mock_popen, mock_gjax):
        mock_popen_instance = MagicMock()
        mock_popen.return_value = mock_popen_instance

        mock_popen_instance.returncode = 0
        mock_popen_instance.communicate = MagicMock()
        mock_popen_instance.communicate.return_value = ("stdout", "stderr")

        mock_gjax.return_value = "job as xml"

        self.jenkins.create_job(self.job)

        assert mock_popen.called
        command = mock_popen.call_args[0][0]
        assert sorted(command) == sorted(self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.CREATE_JOB,
                                                             self.job.name])
        assert mock_gjax.called
        assert mock_popen_instance.communicate.called

        communicate = mock_popen_instance.communicate.call_args[1]
        assert communicate == {"input": mock_gjax.return_value}

        mock_popen_instance.returncode = 1
        assert_raises(platform_ci.jenkins.PlatformJenkinsException, self.jenkins.create_job, self.job)

    @patch('platform_ci.jjb.get_job_as_xml')
    @patch('subprocess.Popen')
    def update_job_test(self, mock_popen, mock_gjax):
        mock_popen_instance = MagicMock()
        mock_popen.return_value = mock_popen_instance

        mock_popen_instance.returncode = 0
        mock_popen_instance.communicate = MagicMock()

        mock_gjax.return_value = "job as xml"

        self.jenkins.update_job(self.job)

        assert mock_popen.called
        command = mock_popen.call_args[0][0]
        assert sorted(command) == sorted(self.jenkins.cli + [platform_ci.jenkins.PlatformJenkinsJavaCLI.UPDATE_JOB,
                                                             self.job.name])
        assert mock_gjax.called
        assert mock_popen_instance.communicate.called

        communicate = mock_popen_instance.communicate.call_args[1]
        assert communicate == {"input": mock_gjax.return_value}

        mock_popen_instance.returncode = 1
        assert_raises(platform_ci.jenkins.PlatformJenkinsException, self.jenkins.update_job, self.job)
