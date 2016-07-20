# Build-on-Push Infrastructure

## Deployment

### Component setup job deployment

### Jenkins Configuration

To fully work, several system-wide environmental variables need to be set on your Jenkins:

 * **BOP_DIST_GIT_URL**: A prefix for constructing git repository URLs
 * **BOP_JENKINS_CLI**: A path (with parameters) where Jenkins CLI is present on Build-on-Push slaves
 * **PLATFORM_CI_ADMINS**: A list of names/email addresses with the Jenkins instance admin contacts

You can configure several other variables; they will improve some job and build descriptions by providing links
to other useful content. If not present, such links will not be provided:

 * **BOP_STAGING_BRANCH_DOC**: A URL to the Staging branch documentation
 * **PLATFORM_CI_BUG_DESTINATION**: A URL to a destination where users can file their bugs and requests
 * **PLATFORM_CI_PROJECT_PAGE**: A URL to a CI project page


### Slave Configuration

The slaves executing the Build-on-Push jobs need the have the following configuration:

 * A Jenkins CLI must be present on the location specified by the master's **BOP_JENKINS_CLI** variable
 * The slave needs to have a private key allowing some Jenkins user to login and create/trigger/update jobs and builds. It is best to use a special key pair for this.
 * The **rhpkg** tool needs to be installed
 * The Jenkins Job Buider needs to be installed