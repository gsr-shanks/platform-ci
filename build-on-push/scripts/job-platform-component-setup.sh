#!/bin/bash -e

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

# Controls the presence of the component triggers on the Jenkins master.

PLATFORM_CI_HOME=${PLATFORM_CI_HOME:-./platform-ci}

if [ ! -d "$PLATFORM_CI_HOME" ]
then
  echo "Cannot find Platform CI code in '$PLATFORM_CI_HOME'" >&2
  echo "Exiting." >&2
  exit 1
fi

BOP_HOME="$PLATFORM_CI_HOME/build-on-push"

. "$BOP_HOME/scripts/functions"

log_header "One-time CI setup"

COMPONENT="$1"
BUILD_ON_COMMIT="$2"
SLAVE="$3"
PLATFORM_CI_REPO="$4"
PLATFORM_CI_BRANCH="$5"

echo "Setting CI for component:       $COMPONENT"
echo "Jobs will run on slave:         $SLAVE"
echo "BUILD_ON_COMMIT will be set to: $BUILD_ON_COMMIT"
echo "Platform CI repo:               $PLATFORM_CI_REPO"
echo "Platform CI branch:             $PLATFORM_CI_BRANCH"

set_current_build_description "$COMPONENT BUILD_ON_COMMIT=$BUILD_ON_COMMIT"

log_header "Checking component sanity"

if ! component_sane "$COMPONENT"; then
  echo "Component '$COMPONENT' does not seem to be valid component name"
  exit 1
else
  echo "Component '$COMPONENT' is sane"
fi

ci_process() {
  local COMMAND="$1"
  local CI="$2"
  local COMPONENT="$3"

  log_header "Setting $CI"
  if [ "$COMMAND" != "do not modify current settings" ];  then
	eval "$BOP_HOME/scripts/ci_$CI" "$COMMAND" "$COMPONENT" "$BOP_HOME/jjb" "$SLAVE" "$PLATFORM_CI_REPO" \
	   "$PLATFORM_CI_BRANCH"
  fi
}

ci_process "$BUILD_ON_COMMIT" commit "$COMPONENT"
