#!/bin/bash
set -euo pipefail

cd /workspace
pip install --no-cache-dir -e ".[docs]"

# Use the repo's hooks (git ignores hooks that are not executable)
git config core.hooksPath .githooks
chmod +x .githooks/*
