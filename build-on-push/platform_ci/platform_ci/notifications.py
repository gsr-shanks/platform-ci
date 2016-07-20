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

"""Notifications: Common notification message construction.

This module implements a message construction mechanisms than can be called
from any callsite in the Platform CI framework, so that the notifications are
consistent for the user and error handling is easy to implement for
the developers: it's just a matter of throwing a exception.

The mechanism consists of two parts: the exceptions and message templates.
The exceptions inheriting from the BaseCIException class carry additional
data members which allow them, when caught, to embed the actual error message
into a reasonable notification email with additional context.
"""

import os
import textwrap

from string import Template

import platform_ci.config

HEADERS = {"GENERIC_CI": "An error has occurred and the desired action was not performed correctly. "
                         "Please contact the administrators of this CI instance.",
           "CONTACTS_CI": "An error has occurred and no tests were reliably executed. ",
           "BREW_BUILD": "There was a problem during a Brew build attempt. ",
           "DIST_GIT": "There was a problem with dist-git manipulation. ",
           "JENKINS": "An error has occurred while communicating with Jenkins. "}


PLATFORM_CI_ADMINS = "Platform CI administrators"


def create_platform_error_header(header_title=HEADERS["CONTACTS_CI"]):
    """Creates a header for a error notification message.

    There are multiple possible headers, depending on what happened (transient
    infrastructure problem may need a different explanation than a CI framework
    bug).

    The actual header is consisting from an explanatory message (what happened)
    and a call to action (what to do). Information needed for the header
    construction are collected from the environment, if available.

    Args:
        header_title: An explanatory message for a class of possible errors

    Returns:
        A string with header to be included in an email notification.
    """

    call_to_action = "Please contact {admins} or file a bug{destination}."

    config = platform_ci.config.PlatformCIConfig()

    if config.admins:
        admins = "{0} ({1})".format(PLATFORM_CI_ADMINS, config.admins)
    else:
        admins = PLATFORM_CI_ADMINS

    if config.bug_destination:
        destination = " at {0}".format(config.bug_destination)
    else:
        destination = ""

    template = header_title + call_to_action
    return template.format(admins=admins, destination=destination)


class BaseCIException(Exception):
    """This class serves as a base of a hierarchy of the CI-related errors.

    The class carries one additional member, *header*. This member is used
    by the code generating the full messages from the caught exceptions.
    """
    header = HEADERS["GENERIC_CI"]


class PlatformCIException(BaseCIException):
    """This exception has a more specific call to action for Platform CI users"""
    header = create_platform_error_header(HEADERS["CONTACTS_CI"])


# pylint: disable=too-few-public-methods
class BrewBuildsErrorNotification(object):
    """Constructs a full error notification message body.

    The message contains the information about a class of an encountered error,
    specific error message, and also the component, Brew target and DistGit
    branch involved in the failed operation. It contains a URL to the Jenkins
    build console log.
    """

    TEMPLATE = """$header

Component:     $component
Branch:        $branch
Brew targets:  $targets

Error message: $message

Debug log: $debug

--
$project_page
"""

    def __init__(self, header, error_message, component, branch, targets):
        self.component = component
        self.branch = branch
        self.targets = " ".join(targets)
        self.message = error_message
        self.header = "\n".join(textwrap.wrap(header))

        if "BUILD_URL" in os.environ:
            self.debug = "%s/console" % os.environ["BUILD_URL"]
        else:
            self.debug = "unknown"

        config = platform_ci.config.PlatformCIConfig()

        if config.project_url:
            self.project_page = "CI Project page: {0}".format(config.project_url)
        else:
            self.project_page = ""

    def __str__(self):
        template = Template(BrewBuildsErrorNotification.TEMPLATE)
        return template.substitute(header=self.header, component=self.component, branch=self.branch,
                                   targets=self.targets, message=str(self.message), debug=self.debug,
                                   project_page=self.project_page)


# pylint: disable=too-few-public-methods
class IndividualBrewBuildResults(object):
    """Constructs individual build attempt result lines for notifications."""
    def __init__(self, builds):
        self.builds = builds

    def __str__(self):
        items = []
        for result in self.builds.all():
            url = result.url
            if url is None:
                if "BUILD_URL" in os.environ:
                    url = "{0}/artifact/{1}".format(os.environ["BUILD_URL"], os.path.basename(result.logfile_path))
                else:
                    url = "No URL available"
            else:
                url = url.strip()
            items.append("  {0} : {1} ({2})".format(result.target, result.short_result, url))
        return "\n".join(items)


class BrewBuildsNotification(object):
    """Constructs full notification message.

    This class constructs a message used when the Brew build requests were
    issued and processed correctly, i.e. when the CI produced reliable, useful
    results for the user to review.

    The message contains the following information about a Jenkins job build:
        - component
        - DistGit branch built
        - a list of targets that were attempted to build
        - result line for each attempted build
        - final verdict
        - link to a Jenkins build console log
    """
    TEMPLATE = """
Component:     $component
Branch:        $branch
Brew targets:  $targets

Final result:  $final_result

Individual results:
$individual_results

Debug log:      $debug_log

--
$project_page
"""

    def __init__(self, builds, component, branch):
        self.template = Template(BrewBuildsNotification.TEMPLATE)
        self.builds = builds
        self.component = component
        self.branch = branch

        if "BUILD_URL" in os.environ:
            self.debug = "%s/console" % os.environ["BUILD_URL"]
        else:
            self.debug = "unknown"

        config = platform_ci.config.PlatformCIConfig()

        if config.project_url:
            self.project_page = "CI Project page: {0}".format(config.project_url)
        else:
            self.project_page = ""

    def __str__(self):
        if self.builds.all_successful():
            final_result = "PASS"
        else:
            final_result = "FAIL (%s builds failed)" % self.builds.count_failed()

        individiual_results = IndividualBrewBuildResults(self.builds)

        return self.template.substitute(component=self.component, branch=self.branch, final_result=final_result,
                                        targets=" ".join(self.builds.targets), individual_results=individiual_results,
                                        debug_log=self.debug, project_page=self.project_page)
