import os


class PlatformCIConfig(object):
    def __init__(self):
        pass

    @property
    def project_url(self):
        return os.environ.get("PLATFORM_CI_PROJECT", None)

    @property
    def distgit_url(self):
        return os.environ.get("BOP_DIST_GIT_URL", None)

    @property
    def jenkins_url(self):
        return os.environ.get("JENKINS_URL", None)

    @property
    def staging_branch_doc_url(self):
        return os.environ.get("BOP_STAGING_BRANCH_DOC", None)

    @property
    def admins(self):
        return os.environ.get("PLATFORM_CI_ADMINS", None)

    @property
    def bug_destination(self):
        return os.environ.get("PLATFORM_CI_BUG_DESTINATION")

    @property
    def jenkins_cli_path(self):
        return os.environ.get("BOP_JENKINS_CLI", None)
