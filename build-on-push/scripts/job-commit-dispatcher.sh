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

PLATFORM_CI_HOME=${PLATFORM_CI_HOME:-./platform-ci}

if [ ! -d "$PLATFORM_CI_HOME" ]
then
  echo "Cannot find Platform CI code in '$PLATFORM_CI_HOME'" >&2
  echo "Exiting." >&2
  exit 1
fi

BOP_HOME="$PLATFORM_CI_HOME/build-on-push"

. "$BOP_HOME/scripts/functions"

log_header "Extracting git branch name"

COMPONENT="$1"
GIT_BRANCH="$2"
SLAVE="$NODE_NAME"
SHORT_GIT_BRANCH=$GIT_BRANCH
PLATFORM_CI_REPO="$3"
PLATFORM_CI_BRANCH="$4"

[[ "$GIT_BRANCH" =~ ^origin/ ]] && SHORT_GIT_BRANCH=$( cut -c '8-' <<< "$GIT_BRANCH" )

echo "Branch name:            $GIT_BRANCH"
echo "Short branch name:      $SHORT_GIT_BRANCH"
echo "Job will run on slave:  $SLAVE"
echo "Platform CI repo:       $PLATFORM_CI_REPO"
echo "Platform CI branch:     $PLATFORM_CI_BRANCH"

set_current_build_description "$SHORT_GIT_BRANCH"

log_header "Checking ci.yaml file"

if [ ! -e "$COMPONENT/ci.yaml" ]
then
  echo "File 'ci.yaml' not found"
  CONFIG_FILE_PARAM=""
else
  echo "File 'ci.yaml' found"
  CONFIG_FILE_PARAM="--config=$COMPONENT/ci.yaml"
fi

log_header "Triggering build job"

eval ci_commit run "$COMPONENT" "$SHORT_GIT_BRANCH" "platform-ci/build-on-push/jjb" "$SLAVE" "$PLATFORM_CI_REPO" \
    "$PLATFORM_CI_BRANCH" "$CONFIG_FILE_PARAM"
