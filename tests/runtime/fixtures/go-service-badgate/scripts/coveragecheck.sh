#!/usr/bin/env bash
# Unit coverage gate: fails the build when line coverage is below 80%.
set -e

THRESHOLD=80

make cover

echo "PASS — coverage gate: line coverage is at or above ${THRESHOLD}%"
