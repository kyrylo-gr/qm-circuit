#!/bin/bash
set -euo pipefail

cd /workspace
pip install --no-cache-dir -e ".[docs]"
