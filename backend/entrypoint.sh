#!/bin/bash

#Move Terraform files
cp -r /app/main.tf /terraform_workspace/
cp -r /app/.terraform.lock.hcl /terraform_workspace/
cp -r /app/versions.tf /terraform_workspace/

set -ex

# Add local user
# Either use the USER_ID if passed in at runtime or
# fallback to 1000

USER_ID=${USER_ID:-1000}
GROUP_ID=${GROUP_ID:-100}

echo "Starting with UID : $USER_ID as user ${USERNAME}"

usermod --uid ${USER_ID} --gid ${GROUP_ID} ${USERNAME}

chown -R ${USERNAME} ${HOME}

gosu ${USERNAME} "$@"
