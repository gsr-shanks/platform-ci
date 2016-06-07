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

import re
import platform_ci.notifications as notifications


class DistGitBranchException(notifications.PlatformCIException):
    """Thrown on errors encountered during work with DistGit branches."""
    header = notifications.create_platform_error_header(notifications.HEADERS["DIST_GIT"])


class DistGitBranch(object):
    """The class represents a DistGit branch.

    The class does not actually interface with DistGit: all methods are
    performed only over the *names* of the branches. There is no dependency
    on actually having access to DistGit or any clone.
    """

    # Standard branch examples: rhel-7.3, extras-rhel-7.2
    STANDARD_BRANCH_REGEXP_PATTERN = r'(?P<st_branch>((extras-)|(rhscl-\d\.\d-rh-\w+?-))?rhel-\d(\.\d)?)$'

    # Staging branch examples:
    #   - Proper staging branches: rhel-7.3-staging, extras-rhel-7.2-staging
    #   - Private staging branches: private-pmuller-rhel-7.3-staging-bz1234567
    #                               private-pmuller-extras-rhel-7.2-staging
    STAGING_BRANCH_REGEXP_PATTERN = r'(?P<st_branch>((extras-)|(rhscl-\d\.\d-rh-\w+?-))?rhel-\d(\.\d)?-staging)'

    STANDARD_BRANCH_REGEXP = re.compile(STANDARD_BRANCH_REGEXP_PATTERN)

    # Note: The branch can be suffixed only if it is private staging branch - has special prefix
    STAGING_BRANCH_REGEXP = re.compile(r'(?P<prefix>private-[\w_-]*?)?' + STAGING_BRANCH_REGEXP_PATTERN +
                                       r'(?(prefix)[\w_-]*?|$)')

    def __init__(self, branch):
        self.name = branch

    def is_staging(self):
        return DistGitBranch.STAGING_BRANCH_REGEXP.match(self.name) is not None

    def is_standard(self):
        return DistGitBranch.STANDARD_BRANCH_REGEXP.match(self.name) is not None

    @property
    def staging_target(self):
        """Computes a Brew target name matching the branch

        Returns: A name of the Brew target associated with the branch name

        Example: DistGitBranch("rhel-7.3-staging").staging_target -> "rhel-7.3-candidate"
        """
        if self.is_staging():
            # Use just the staging branch name match
            staging_branch_base = DistGitBranch.STAGING_BRANCH_REGEXP.match(self.name).group('st_branch')

            # TODO: if the staging branch will be e.g. "rhel-6-staging", the target would be determined incorrectly
            # We would have to get the latest RHEL-6 target and use that.
            return staging_branch_base.replace("staging", "candidate")
        elif self.is_standard():
            # Use just the staging branch name match
            standard_branch_base = DistGitBranch.STANDARD_BRANCH_REGEXP.match(self.name).group('st_branch')

            # TODO: if the staging branch will be e.g. "rhel-6-staging", the target would be determined incorrectly
            # We would have to get the latest RHEL-6 target and use that.
            return standard_branch_base + "-candidate"

        raise DistGitBranchException("%s is not a staging or standard branch" % self.name)

    @property
    def type(self):
        """Returns a type of the branch.

        There are four branch types: official, staging, private, and private staging.
        The type is determined from the branch name. A staging branch is named as a
        standard branch with '-staging' suffix. A private staging branch is a well-named
        private branch (with private- prefix) containing a name of a staging branch inside.
        Any other name is considered to be private branch.

        Examples:
            official: rhel-6.8
            staging: rhel-6.8-staging
            private staging: private-<anything->rhel-6.8-staging<-anything>
            private: john-feature-branch-bz123321

        Returns:
            One of the strings ['standard','staging','private','private staging']
        """
        if self.is_staging():
            if self.name.startswith("private-"):
                return "private staging"
            else:
                return "staging"
        elif self.is_standard():
            return "standard"

        return "private"
