#!/usr/bin/env bash
# update-helm-tag.sh
# Usage: update-helm-tag.sh <VALUES_FILE> <TAG>
#
# Arguments:
#   $1 = VALUES_FILE  (path to the Helm values.yaml file to update)
#   $2 = TAG          (new image tag value, e.g. "a3f9d1c")
#
# Updates any line matching ^\s*tag:\s* in VALUES_FILE, replacing the value
# with the quoted TAG. All other YAML fields and structure are preserved.
# The operation is idempotent: applying it twice with the same tag produces
# the same result as applying it once.

set -euo pipefail

VALUES_FILE="${1:-}"
TAG="${2:-}"

if [ -z "${VALUES_FILE}" ] || [ -z "${TAG}" ]; then
  echo "Usage: $(basename "$0") <VALUES_FILE> <TAG>" >&2
  echo "  VALUES_FILE  path to the Helm values.yaml file" >&2
  echo "  TAG          new image tag value (e.g. a3f9d1c)" >&2
  exit 1
fi

sed -i "s/^\(\s*tag:\s*\).*$/\1\"${TAG}\"/" "${VALUES_FILE}"
