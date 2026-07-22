#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=src
uv run uvicorn ecosfera_ai.main:app --reload --app-dir src
