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
from mock import MagicMock, patch
# pylint: disable=no-name-in-module
from nose.tools import assert_raises

from platform_ci.distgit import DistGitBranch, DistGitBranchException
from platform_ci.ci_types import CommitCI, CommitCIConfig, PlatformCISource


# pylint: disable=no-member,wrong-import-position,wrong-import-order
try:
    major = version_info.major
except AttributeError:
    major = version_info[0]

# pylint: disable=import-error
if major == 2:
    import __builtin__ as builtins
else:
    import builtins


# pylint: disable=too-many-public-methods
class CommitCIConfigTest(unittest.TestCase):

    TEST_TARGET = "rhel-7.1-candidate"

    # pylint: disable=no-self-use
    @patch('yaml.load')
    @patch.object(builtins, 'open')
    def test_sanity(self, mock_open, mock_yaml_load):
        mock_yaml_load.return_value = {"auto-build": {"targets": [CommitCIConfigTest.TEST_TARGET]}}
        config = CommitCIConfig("some_path")
        assert mock_open.called
        assert mock_yaml_load.called
        assert config.targets == [CommitCIConfigTest.TEST_TARGET]


# pylint: disable=too-many-public-methods
class CommitCITest(unittest.TestCase):

    TEST_COMPONENT = "test-component"
    TEST_TARGETS = ["test-1-target", "test-2-target"]
    TEST_BRANCH = "test-branch"
    TEST_CONFIG_FILE = "/file/to/path"
    TEST_STAGING_BRANCH = "rhel-6.7-staging"
    TEST_STAGING_TARGET = "rhel-6.7-candidate"
    TEST_SLAVE = "team-slave"
    TEST_PLATFORM_CI_BRANCH = "test-branch"
    TEST_GITHUB_USER = "RHQE"
    TEST_PLATFORM_CODE_SOURCE = PlatformCISource(TEST_GITHUB_USER, TEST_PLATFORM_CI_BRANCH)

    def setUp(self):
        self.jenkins = MagicMock()
        self.commitci = CommitCI(self.jenkins, CommitCITest.TEST_COMPONENT)

    def test_enable_when_not_exists(self):
        self.jenkins.job_exists.return_value = False
        self.commitci.enable(CommitCITest.TEST_SLAVE, CommitCITest.TEST_PLATFORM_CODE_SOURCE)
        assert self.jenkins.job_exists.called
        assert self.jenkins.create_job.called

    def test_enable_when_exists(self):
        self.jenkins.job_exists.return_value = True
        self.commitci.enable(CommitCITest.TEST_SLAVE, CommitCITest.TEST_PLATFORM_CODE_SOURCE)
        assert self.jenkins.job_exists.called
        assert not self.jenkins.create_job.called
        assert self.jenkins.update_job.called
        assert self.jenkins.enable_job.called

    # pylint: disable=protected-access
    def test_enable(self):
        self.commitci._enable_job = MagicMock()
        self.commitci.enable(CommitCITest.TEST_SLAVE, CommitCITest.TEST_PLATFORM_CODE_SOURCE)

        assert self.commitci._enable_job.called
        job = self.commitci._enable_job.call_args[0][0]
        assert job.component == CommitCITest.TEST_COMPONENT

    @patch('platform_ci.ci_types.CommitCIConfig')
    def test_run_by_config(self, mock_commitconfig):
        mock_commitconfig.return_value = MagicMock()
        mock_commitconfig.return_value.targets = CommitCITest.TEST_TARGETS
        self.commitci._run_on_targets = MagicMock()

        self.commitci._run_by_config(DistGitBranch(CommitCITest.TEST_BRANCH), CommitCITest.TEST_SLAVE,
                                     CommitCITest.TEST_PLATFORM_CODE_SOURCE, CommitCITest.TEST_CONFIG_FILE)
        assert self.commitci._run_on_targets.called
        assert self.commitci._run_on_targets.call_args[0][0] == CommitCITest.TEST_BRANCH
        assert self.commitci._run_on_targets.call_args[0][1] == CommitCITest.TEST_TARGETS

    def test_run_on_staging(self):
        self.commitci._run_on_targets = MagicMock()
        staging = DistGitBranch(CommitCITest.TEST_STAGING_BRANCH)

        self.commitci._run_on_staging(staging, CommitCITest.TEST_SLAVE, CommitCITest.TEST_PLATFORM_CODE_SOURCE)
        assert self.commitci._run_on_targets.called
        assert self.commitci._run_on_targets.call_args[0][0] == CommitCITest.TEST_STAGING_BRANCH
        assert self.commitci._run_on_targets.call_args[0][1] == [CommitCITest.TEST_STAGING_TARGET]

    @patch('platform_ci.ci_types.CommitCIConfig')
    def test_run_on_staging_with_config(self, mock_commitconfig):
        mock_commitconfig.return_value = MagicMock()
        mock_commitconfig.return_value.targets = CommitCITest.TEST_TARGETS
        staging = DistGitBranch(CommitCITest.TEST_STAGING_BRANCH)
        self.commitci._run_on_targets = MagicMock()

        self.commitci._run_on_staging(staging, CommitCITest.TEST_SLAVE, CommitCITest.TEST_PLATFORM_CODE_SOURCE,
                                      CommitCITest.TEST_CONFIG_FILE)

        assert self.commitci._run_on_targets.called
        assert self.commitci._run_on_targets.call_args[0][0] == CommitCITest.TEST_STAGING_BRANCH
        expected_targets = CommitCITest.TEST_TARGETS + [CommitCITest.TEST_STAGING_TARGET]
        assert self.commitci._run_on_targets.call_args[0][1] == expected_targets

    def test_run_on_staging_invalid(self):
        staging = DistGitBranch(CommitCITest.TEST_BRANCH)
        assert_raises(DistGitBranchException, self.commitci._run_on_staging, staging, CommitCITest.TEST_SLAVE,
                      CommitCITest.TEST_PLATFORM_CODE_SOURCE)
