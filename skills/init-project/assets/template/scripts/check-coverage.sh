#!/usr/bin/env bash

set -euo pipefail

profile="${1:-cover.profile}"
threshold="${2:-80}"

if [[ ! -f "${profile}" ]]; then
	echo "coverage profile not found: ${profile}" >&2
	exit 2
fi

if [[ ! "${threshold}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
	echo "coverage threshold must be numeric: ${threshold}" >&2
	exit 2
fi

filtered_profile="$(mktemp)"
trap 'rm -f "${filtered_profile}"' EXIT

# Generated code and test-support helpers are outside the hand-written production metric.
awk 'NR == 1 || ($1 !~ /\/mocks\// && $1 !~ /\/sqlc\// && $1 !~ /\/valkeytest\// && $1 !~ /\/clocktest\// && $1 !~ /\/idgentest\//)' \
	"${profile}" >"${filtered_profile}"

report="$(go tool cover -func="${filtered_profile}")"
printf '%s\n' "${report}"

actual="$(printf '%s\n' "${report}" | awk '/^total:/ {gsub(/%/, "", $3); print $3}')"
if [[ -z "${actual}" ]]; then
	echo "coverage total not found in report" >&2
	exit 2
fi

if ! awk -v actual="${actual}" -v threshold="${threshold}" 'BEGIN { exit !(actual + 0 >= threshold + 0) }'; then
	echo "coverage gate failed: ${actual}% < ${threshold}%" >&2
	exit 1
fi

echo "coverage gate passed: ${actual}% >= ${threshold}%"
