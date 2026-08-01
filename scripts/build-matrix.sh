#!/usr/bin/env bash
# build-matrix.sh
# Usage: build-matrix.sh <ui> <cart> <catalog> <checkout> <orders> <event_name>
#
# Arguments:
#   $1 = ui flag        (true/false)
#   $2 = cart flag      (true/false)
#   $3 = catalog flag   (true/false)
#   $4 = checkout flag  (true/false)
#   $5 = orders flag    (true/false)
#   $6 = event_name     (e.g. "push", "workflow_dispatch")
#
# Writes a JSON array of service names to stdout.
# If event_name is "workflow_dispatch", always outputs all five services.
# Otherwise, outputs only services whose flag is "true".
# If no services match, outputs [].

set -euo pipefail

UI_FLAG="${1:-false}"
CART_FLAG="${2:-false}"
CATALOG_FLAG="${3:-false}"
CHECKOUT_FLAG="${4:-false}"
ORDERS_FLAG="${5:-false}"
EVENT_NAME="${6:-push}"

if [ "${EVENT_NAME}" = "workflow_dispatch" ]; then
  echo '["ui","cart","catalog","checkout","orders"]'
  exit 0
fi

SERVICES=()

[ "${UI_FLAG}" = "true" ]       && SERVICES+=("ui")
[ "${CART_FLAG}" = "true" ]     && SERVICES+=("cart")
[ "${CATALOG_FLAG}" = "true" ]  && SERVICES+=("catalog")
[ "${CHECKOUT_FLAG}" = "true" ] && SERVICES+=("checkout")
[ "${ORDERS_FLAG}" = "true" ]   && SERVICES+=("orders")

if [ "${#SERVICES[@]}" -eq 0 ]; then
  echo '[]'
  exit 0
fi

MATRIX=$(printf '"%s",' "${SERVICES[@]}" | sed 's/,$//')
echo "[${MATRIX}]"
