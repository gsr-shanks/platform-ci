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

"""This module contains representations of the individual Jenkins job "types"""

import yaml

import platform_ci.notifications as notifications
import platform_ci.config


# pylint: disable=too-few-public-methods
class JenkinsJobError(notifications.PlatformCIException):
    """Exception to be used on errors during work with Jenkins jobs."""
    header = notifications.create_platform_error_header()


class JobBuildOnCommit(object):
    """Represents a Build-on-Push worker job.

    The worker job issues scratch build requests in Brew. For a component,
    there should be a single Worker job per DistGit branch, so it's build
    history represents a build-ability of that branch in history.
    """
    def __init__(self, component, branch, slave, platform_ci_source):
        self.component = component
        self.branch = branch
        self.slave = slave
        self.platform_ci_source = platform_ci_source

    @staticmethod
    def create_job_name(component, branch):
        """Creates a name of a job.

        This method exists so that call-sites without the information about
        further details about a Worker job (such as slave and Platform CI repo
        branch) can construct names of jobs, so that they can e.g. trigger them.

        Args:
            Component: Component name
            Branch: DistGit branch name

        Returns:
            Name of the Worker job for a given component and branch
        """
        return "ci-%s-commit-%s" % (component, branch)

    @property
    def name(self):
        """Returns the name of the Jenkins job represented by this instance."""
        return JobBuildOnCommit.create_job_name(self.component, self.branch)

    @property
    def display_name(self):
        """Returns the human-oriented label of the job represented by an instance."""
        return "{0}: Build branch {1} in Brew".format(self.component, self.branch)

    def as_yaml(self):
        """Returns a YAML string usable for instantiation of the JJB template.

        The output is the YAML with values which can be used to instantiate
        the 'ci-workflow-brew-build' template to create a Jenkins job using the
        Jenkins Job Builder.
        """

        config = platform_ci.config.PlatformCIConfig()

        if config.project_url:
            platform_ci_project_link = '<a href="{0}">Platform CI Project</a>'.format(config.project_url)
        else:
            platform_ci_project_link = "Platform CI Project"

        if not config.distgit_url:
            raise JenkinsJobError("DistGit URL not set: cannot create a commit worker job")

        if config.jenkins_url:
            dispatcher_name = JobCommitDispatcher.create_job_name(self.component)
            dispatcher_link = '<a href="{0}/job/{1}">commit dispatcher</a>'.format(config.jenkins_url, dispatcher_name)
        else:
            dispatcher_link = 'commit dispatcher'

        template = {"job-template": {"name": self.name, "defaults": "ci-workflow-brew-build"}}
        project = {"project": {"name": self.component, "component": self.component, "jobs": [self.name],
                               "git-branch": self.branch, "display-name": self.display_name, "team-slave": self.slave,
                               "platform-ci-branch": self.platform_ci_source.branch, 'dispatcher-link': dispatcher_link,
                               "platform-ci-project-link": platform_ci_project_link,
                               "distgit-root-url": config.distgit_url, "github-user": self.platform_ci_source.user}}

        return yaml.dump([template, project], default_flow_style=False)


class JobCommitDispatcher(object):
    """Represents the Build-on-Push dispatcher job.

    The dispatcher job monitors all changes in a DistGit repository for a given
    component, and based on the branch where the changes were made, decides if
    the testing scratch-build should be automatically attempted. There should be
    a single dispatcher job per component.
    """
    def __init__(self, component, slave=None, platform_ci_source=None):
        self.component = component
        self.slave = slave
        self.platform_ci_source = platform_ci_source

    @staticmethod
    def create_description(commit, built_targets, jenkins_url, component):
        """Creates a build description for the dispatcher job.

        Args:
            commit: A DistGitCommit that caused this dispatcher to run
            built_targets: A list of targets that were decided to build
            jenkins_url: The URL of the Jenkins master where the description will be viewed.
            component: A name of the component
        Returns:
            A string with the HTML fragment suitable to be used as a Jenkins job build
                description
        """
        branch = commit.branch
        lines = ["<strong>Dist-git branch</strong>: {0.name} ({0.type} branch)".format(branch)]

        if commit.hash:
            lines.append("<strong>Commit:</strong> {0}".format(commit.hash))

        if not built_targets:
            lines.append("<strong>No brew build was issued</strong> ({0.name} is not handled by CI)".format(branch))
        else:
            trigger_job_template = '<strong>Triggered job: </strong><a href="{0}/job/{1}">Worker job for branch {2}</a>'
            worker_job_name = JobBuildOnCommit.create_job_name(component, branch.name)
            trigger_job_message = trigger_job_template.format(jenkins_url, worker_job_name, branch.name)
            lines.append(trigger_job_message)

        if commit.description:
            lines.append("<hr/><strong>Commit description:</strong>")
            lines.extend(commit.description.split("\n"))

        return "<p>{0}</p>".format("<br>".join(lines))

    @staticmethod
    def create_job_name(component):
        return "ci-{0}-dispatcher-commit".format(component)

    @property
    def name(self):
        """Returns the name of the job represented by an instance."""
        return JobCommitDispatcher.create_job_name(self.component)

    @property
    def display_name(self):
        """Returns the (human-oriented) label of a job represented by an instance."""
        return "{0}: Schedule Brew build".format(self.component)

    def as_yaml(self):
        """Returns a YAML string usable for instantiation of the JJB template.

        The output is the YAML with values which can be used to instantiate
        the 'ci-dispatcher-commit' template to create a Jenkins job using the
        Jenkins Job Builder.
        """

        config = platform_ci.config.PlatformCIConfig()

        # TODO: These settings should be centralized somewhere else
        if config.project_url:
            platform_ci_project_link = '<a href="{0}">Platform CI Project</a>'.format(config.project_url)
        else:
            platform_ci_project_link = "Platform CI Project"

        if not config.distgit_url:
            raise JenkinsJobError("DistGit URL not set: cannot create a commit dispatcher job")

        if config.staging_branch_doc_url:
            staging_branch_doc_link = '<a href="{0}">staging branch</a>'.format(config.staging_branch_doc_url)
        else:
            staging_branch_doc_link = "staging branch"

        template = {"job-template": {"name": self.name, "defaults": 'ci-dispatcher-commit'}}
        project = {"project": {"name": self.component, "component": self.component, "jobs": [self.name],
                               "display-name": self.display_name, "team-slave": self.slave,
                               "platform-ci-branch": self.platform_ci_source.branch,
                               "distgit-root-url": config.distgit_url,
                               "platform-ci-project-link": platform_ci_project_link,
                               "staging-branch-doc-link": staging_branch_doc_link,
                               "github-user": self.platform_ci_source.user}}

        return yaml.dump([template, project], default_flow_style=False)
