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

# pylint: disable=no-name-in-module
from nose.tools import assert_raises

from .distgit import DistGitBranch, DistGitBranchException


class DistGitBranchTest(unittest.TestCase):
    STAGING = {"branch": "rhel-7.1-staging", "target": "rhel-7.1-candidate"}
    PRIVATE = {"branch": "private-pmuller-branch", "target": None}
    STANDARD = {"branch": "extras-rhel-7.2", "target": "extras-rhel-7.2-candidate"}
    EXTRAS_STAGING = {"branch": "extras-rhel-7.2-staging", "target": "extras-rhel-7.2-candidate"}

    def setUp(self):
        self.staging_branch = DistGitBranch(DistGitBranchTest.STAGING["branch"])
        self.private_branch = DistGitBranch(DistGitBranchTest.PRIVATE["branch"])
        self.extras_staging_branch = DistGitBranch(DistGitBranchTest.EXTRAS_STAGING["branch"])
        self.standard_branch = DistGitBranch(DistGitBranchTest.STANDARD["branch"])

    def extras_staging_branch_test(self):
        assert self.extras_staging_branch.name == DistGitBranchTest.EXTRAS_STAGING["branch"]
        assert self.extras_staging_branch.is_staging()
        assert self.extras_staging_branch.staging_target == DistGitBranchTest.EXTRAS_STAGING["target"]
        assert self.extras_staging_branch.type == "staging"

    def staging_branch_test(self):
        assert self.staging_branch.name == DistGitBranchTest.STAGING["branch"]
        assert self.staging_branch.is_staging()
        assert self.staging_branch.staging_target == DistGitBranchTest.STAGING["target"]
        assert self.staging_branch.type == "staging"

    def private_branch_test(self):
        assert self.private_branch.name == DistGitBranchTest.PRIVATE["branch"]
        assert not self.private_branch.is_staging()
        assert_raises(DistGitBranchException, lambda: self.private_branch.staging_target)
        assert self.private_branch.type == "private"

    def standard_branch_test(self):
        assert self.standard_branch.name == DistGitBranchTest.STANDARD["branch"]
        assert not self.standard_branch.is_staging()
        print self.standard_branch.staging_target
        assert self.standard_branch.staging_target == DistGitBranchTest.STANDARD["target"]
        assert self.standard_branch.type == "standard"

    # pylint: disable=no-self-use
    def rhscl_staging_branch_test(self):
        """
        Tests for parsing staging branches for RHSCL and determining the correct build target
        """
        testing_branches = [
            'rhscl-2.1-rh-ruby22-rhel-6-staging',
            'rhscl-2.1-rh-ruby22-rhel-7-staging',
            'rhscl-2.1-rh-mariadb100-rhel-6-staging',
            'rhscl-2.1-rh-mariadb100-rhel-7-staging'
        ]

        testing_targets = [branch.replace('staging', 'candidate') for branch in testing_branches]

        for branch, target in zip(testing_branches, testing_targets):
            obj = DistGitBranch(branch)
            assert obj.is_staging()
            assert obj.staging_target == target
            assert obj.type == "staging"

    # pylint: disable=no-self-use
    def private_rhscl_staging_branch_test(self):
        """
        Tests for parsing private staging branches for RHSCL and determining the correct build target
        """
        testing_data = [
            ('private-johnfoo-rhscl-2.1-rh-ruby22-rhel-6-staging', 'rhscl-2.1-rh-ruby22-rhel-6-candidate'),
            ('private-johnfoo-rhscl-2.1-rh-ruby22-rhel-7-staging-BZ123456', 'rhscl-2.1-rh-ruby22-rhel-7-candidate'),
            ('private-rhscl-2.1-rh-mariadb100-rhel-6-staging-BZ654321', 'rhscl-2.1-rh-mariadb100-rhel-6-candidate'),
            ('private-jo-fo-rhscl-2.1-rh-mariadb100-rhel-7-staging-bar-baz', 'rhscl-2.1-rh-mariadb100-rhel-7-candidate')
        ]

        for branch, target in testing_data:
            obj = DistGitBranch(branch)
            assert obj.is_staging()
            assert obj.staging_target == target
            assert obj.type == "private staging"

    # pylint: disable=no-self-use
    def private_staging_branch_test(self):
        """
        Tests for parsing private staging branches for RHEL components and determining the correct build target
        """
        testing_data = [
            ('private-johnfoo-rhel-7.3-staging', 'rhel-7.3-candidate'),
            ('private-johnfoo-rhel-7.3-staging-BZ123456', 'rhel-7.3-candidate'),
            ('private-rhel-6.8-staging-BZ654321', 'rhel-6.8-candidate'),
            ('private-jo-fo-rhel-6.8-staging-bar-baz', 'rhel-6.8-candidate'),
            ('private-johnfoo-extras-rhel-7.3-staging', 'extras-rhel-7.3-candidate'),
            ('private-johnfoo-extras-rhel-7.3-staging-BZ123456', 'extras-rhel-7.3-candidate'),
            ('private-extras-rhel-6.8-staging-BZ654321', 'extras-rhel-6.8-candidate'),
            ('private-jo-fo-extras-rhel-6.8-staging-bar-baz', 'extras-rhel-6.8-candidate'),
        ]

        for branch, target in testing_data:
            obj = DistGitBranch(branch)
            assert obj.is_staging()
            assert obj.staging_target == target
            assert obj.type == "private staging"
