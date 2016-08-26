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
This module provides a very thin wrapper over the Jenkins Job Builder. It's
sole purpose is to generate instantiated job XML definitions using the JJB
'test' command.
"""

import tempfile
import os
import shutil
import subprocess


def get_job_as_xml(job, template_dir):
    """Returns a instantiated definition of a Jenkins job in XML format.

    Args:
        job: A Jenkins Job object to be instantiated
        template_dir: A path to a directory containing job templates

    Returns:
        A string with the XML definition of a Jenkins job, suitable to be
            used as an input for Jenkins API to create/update a job.
    """
    with JJB(template_dir) as jjbuilder:
        jobxml = jjbuilder.get_job_as_xml(job)
    return jobxml


# pylint: disable=too-few-public-methods
class JJB(object):
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self.workdir = tempfile.mkdtemp()

    def __enter__(self):
        for item in os.listdir(self.template_dir):
            source_path = os.path.join(self.template_dir, item)
            if os.path.isfile(source_path):
                shutil.copy(source_path, self.workdir)

        return self

    def __exit__(self, type_param, value, traceback):
        shutil.rmtree(self.workdir)

    def get_job_as_xml(self, job):
        with open(os.path.join(self.workdir, "%s.yaml" % job.name), "w") as job_file:
            job_file.write(job.as_yaml())

        jjb = subprocess.Popen(["jenkins-jobs", "test", self.workdir, job.name], stdout=subprocess.PIPE)
        jjb_xml = jjb.communicate()[0]
        return jjb_xml
