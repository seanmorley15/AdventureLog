#!/bin/sh
set -e

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

git config core.hooksPath .githooks
echo "Git hooks enabled (core.hooksPath=.githooks)"
