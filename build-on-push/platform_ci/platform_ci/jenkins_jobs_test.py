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

import unittest
import yaml
import os
from .jenkins_jobs import JobBuildOnCommit, JobCommitDispatcher
from .ci_types import PlatformCISource


# pylint: disable=too-many-public-methods
class JobBuildOnCommitTest(unittest.TestCase):

    def setUp(self):
        self.component = "glibc"
        self.branch = "rhel-7.1"
        self.slave = "slave-name"
        self.platform_ci_branch = "test-branch"
        self.github_user = "QEOS"
        self.platform_ci_source = PlatformCISource(self.github_user, self.platform_ci_branch)

        self.job = JobBuildOnCommit(self.component, self.branch, self.slave, self.platform_ci_source)

    def test_sanity(self):
        assert self.component == self.job.component
        assert self.job.name == "ci-%s-commit-%s" % (self.component, self.branch)
        assert self.branch == self.job.branch
        assert self.slave == self.job.slave
        assert self.job.display_name == "glibc: Build branch rhel-7.1 in Brew"

    def test_as_yaml(self):
        os.environ["BOP_DIST_GIT_URL"] = "git://fake/url"
        as_yaml = self.job.as_yaml()
        reconstructed = yaml.load(as_yaml)
        assert len(reconstructed) == 2


class JobCommitDispatcherTest(unittest.TestCase):
    def setUp(self):
        self.component1 = "glibc"
        self.component2 = "gcc"
        self.slave = "slave-name"
        self.platform_ci_branch = "test-branch"
        self.platform_ci_source = PlatformCISource("RHQE", self.platform_ci_branch)
        self.job_component1 = JobCommitDispatcher(self.component1, self.slave, self.platform_ci_source)
        self.job_component2 = JobCommitDispatcher(self.component2, self.slave, self.platform_ci_source)

    def test_slave(self):
        assert self.slave == self.job_component1.slave

    def test_platform_ci_branch(self):
        assert self.platform_ci_branch == self.job_component1.platform_ci_source.branch

    def test_name(self):
        assert "ci-{0}-dispatcher-commit".format(self.component1) == self.job_component1.name
        assert "ci-{0}-dispatcher-commit".format(self.component2) == self.job_component2.name

    def test_display_name(self):
        assert "{0}: Schedule Brew build".format(self.component1) == self.job_component1.display_name
        assert "{0}: Schedule Brew build".format(self.component2) == self.job_component2.display_name
