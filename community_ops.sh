#!/bin/bash
# community_ops.sh - Community Operations Platform CLI wrapper
# Usage: community_ops.sh <command> [args...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/community_ops.py" "$@"
