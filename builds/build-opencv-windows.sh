#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ps_script="$(cygpath -w "${script_dir}/build-opencv-windows.ps1")"
args=(-NoProfile -ExecutionPolicy Bypass -File "${ps_script}")
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [target-python]" >&2
  exit 2
fi
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [target-python]"
  exit 0
fi
if [[ $# -eq 1 ]]; then
  args+=(-TargetPython "$(cygpath -w "$1")")
fi
powershell.exe "${args[@]}"
