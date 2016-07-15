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

"""This module implements the "CI for Component" concept.

A "CI for Component" is a high-level concept: if a certain CI functionality
is enabled for a component, it means a certain set of Jenkins jobs need
to be present and enabled on a Jenkins instance. The classes in this module
represent such CI functionality: they understand which jobs are needed,
how to create or disable them and how to run their individual parts.
"""

import logging
import yaml
from .jenkins_jobs import JobCommitDispatcher, JobBuildOnCommit


class PlatformCISource(object):
    """This class represents a Platform CI code source.

    Platform CI code source is a GitHub repository, defined by a user and
    optionally by a branch."""

    # pylint: disable=too-few-public-methods

    def __init__(self, gh_user, branch="master"):
        self.user = gh_user
        self.branch = branch


# pylint: disable=too-few-public-methods
class PlatformCI(object):
    """Base class for further extension.

    Provides basic job operations over a Jenkins instance.
    """
    def __init__(self, jenkins, component):
        self.component = component
        self.jenkins = jenkins

    def _delete_job(self, job):
        """Deletes a job from Jenkins.

        Does nothing if the job does not exist.
        """
        if self.jenkins.job_exists(job):
            self.jenkins.delete_job(job)

    def _enable_job(self, job):
        """Enables a job on Jenkins.

        If the job does not exist, it is created. If the job exists, it is
        updated using the current JJB templates.
        """
        if self.jenkins.job_exists(job):
            self.jenkins.update_job(job)
            self.jenkins.enable_job(job)
        else:
            self.jenkins.create_job(job)

    def _disable_job(self, job):
        """Disables job on Jenkins.

        Does nothing if the job does not exist.
        """
        if self.jenkins.job_exists(job):
            self.jenkins.disable_job(job)


# pylint: disable=too-few-public-methods
class CommitCIConfig(object):
    """Small class representing the ci.yaml control file.

    Developers can include a ci.yaml control file in their repository branches
    to indicate such branch should be automatically built and tested (similar
    to how Travis CI works).
    """
    def __init__(self, ci_file_path):
        with open(ci_file_path, 'r') as ci_file:
            ci_config = yaml.load(ci_file)
            self.targets = ci_config["auto-build"]["targets"]


class CommitCI(PlatformCI):
    """Implements the Build-on-Push CI functionality.

    The Build-on-Push is a universal CI mechanism allowing automated issue
    of testing (scratch) builds whenever there are new commits in a given
    DistGit branch pushed to a central, monitored location.

    Currently there are two mechanisms which decide which branches of a DistGit
    repository should be built: first, it's a *staging branch* concept which
    recognizes the importance of a branch from the branch name. Second, the
    developers can put a simple YAML config file to a branch, indicating
    such branch should be also automatically built.

    Build-on-Push CI consists of two types of jobs: a single *dispatcher* job
    monitors events in the whole repository, and whenever there are any new
    commits in any branch, it decides if the branch should be automatically
    built. If yes, it triggers a *worker* job for a given branch: there is
    a single *worker* job per DistGit branch, and its only job is to issue
    a scratch build request to Brew.
    """
    def __init__(self, jenkins, component):
        super(CommitCI, self).__init__(jenkins, component)

    def enable(self, slave, platform_ci_source):
        """Enable Build-on-Push for a component.

        Implementation-wise, create or enable a dispatcher job for a given
        component.

        Args:
            slave: A name of a Jenkins slave that will run the created jobs
            platform_ci_source: A PlatformCISource instance describing desired
                Platform CI code source.
        """
        dispatcher = JobCommitDispatcher(self.component, slave, platform_ci_source)

        self._enable_job(dispatcher)

    def disable(self):
        """Disable Build-on-Push for a component."""
        dispatcher = JobCommitDispatcher(self.component)

        self._disable_job(dispatcher)

    def _run_on_targets(self, branch, targets, slave, platform_ci_source):
        """Trigger a worker job building a dist-git branch in several targets.

        There is a single worker job per dist-git branch. If a worker job
        does not exist, is disabled or has different configuration the method
        creates/enables/reconfigures it.

        Args:
            branch: A dist-git branch name
            targets: A sequence of Brew target names
            slave: A slave name on which the worker job should be executed
            platform_ci_source: A PlatformCISource instance describing the repo
                from which the code will be fetched inside the worker job.
        """

        worker = JobBuildOnCommit(self.component, branch, slave, platform_ci_source)
        self._enable_job(worker)
        self.jenkins.trigger_job(worker, parameters={"BREW_TARGETS": " ".join(targets)})

    def _run_on_staging(self, staging_branch, slave, platform_ci_source, config_file=None):
        """Trigger a worker job building a staging branch in its associated Brew target.

        There is a single worker job per dist-git branch. If a worker job
        does not exist, is disabled or has different configuration the method
        creates/enables/reconfigures it. A staging branch has a single associated
        Brew target: this target is always built. Additionally, any target specified
        in the ci.yaml file (if present) is built too.

        Args:
            staging_branch: A DistGitBranch instance representing a branch. It must
                have a 'staging' or 'private staging' type.
            slave: A slave name on which the worker job should be executed
            platform_ci_source: A PlatformCISource instance describing the repo
                from which the code will be fetched inside the worker job.
            config_file: A path to a config file inside a dist-git branch.

        Returns:
            A list of target names that will be built in the triggered job.

        Raises:
            distgit.DistGutBranchException: Passed staging_branch is not a staging branch.
        """

        if config_file is not None:
            logging.info("Config file is present in the branch: %s", config_file)
            config = CommitCIConfig(config_file)
            targets = list(config.targets)
            logging.info("Targets from config file: %s", str(targets))
        else:
            logging.info("Config file is not present in the branch: no targets aside of staging target will be tested")
            targets = []

        staging_target = staging_branch.staging_target
        logging.info("Staging target: %s", staging_target)

        if staging_target not in targets:
            targets.append(staging_target)

        self._run_on_targets(staging_branch.name, targets, slave, platform_ci_source)
        return targets

    def _run_by_config(self, branch, slave, platform_ci_source, config_file):
        """Trigger a worker job building a branch in targets specified in a config file.

        There is a single worker job per dist-git branch. If a worker job
        does not exist, is disabled or has different configuration the method
        creates/enables/reconfigures it.

        Args:
            branch: A DistGitBranch instance representing a branch
            slave: A slave name on which the worker job should be executed
            platform_ci_source: A PlatformCISource instance describing the repo
                from which the code will be fetched inside the worker job.
            config_file: A path to a config file inside a dist-git branch.

        Returns:
            A list of target names that will be built in the triggered job.
        """
        config = CommitCIConfig(config_file)
        logging.info("Targets from config file: %s", config.targets)
        self._run_on_targets(branch.name, config.targets, slave, platform_ci_source)
        return config.targets

    def consider_build(self, commit, slave, platform_ci_source, config_file):
        """Trigger a worker job for a branch, depending on the branch type.

        Trigger a worker job either if branch is a staging branch or a private
        staging branch, or if there is a CI config file present in a branch. Do
        not trigger a worker job otherwise. If a job is triggered and this method
        is run inside a Jenkins job build, set a description of that build.

        Args:
            commit: A DistGitCommit representing a considered commit
            slave: A slave name on which the worker job should be executed
            platform_ci_source: A PlatformCISource instance describing the repo
                from which the code will be fetched inside the worker job.
            config_file: A path to a config file inside a dist-git branch, or None
        """

        branch = commit.branch

        if branch.is_staging():
            logging.info("Branch [%s] should be built: it is a staging branch", branch.name)
            built_targets = self._run_on_staging(branch, slave, platform_ci_source, config_file)
        elif config_file is not None:
            logging.info("Branch [%s] should be built: it contains a 'ci.yaml' file", branch.name)
            built_targets = self._run_by_config(branch, slave, platform_ci_source, config_file)
        else:
            logging.warning("Branch [%s] is not a staging branch and 'ci.yaml' file was not found", branch.name)
            logging.warning("Branch [%s] should not be built", branch.name)
            built_targets = []

        description = JobCommitDispatcher.create_description(commit, built_targets, self.jenkins.url, self.component)
        self.jenkins.set_current_build_description(description)
