#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ps_script="$(cygpath -w "${script_dir}/build-windows.ps1")"
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--candidate]" >&2
  exit 2
fi
case "${1:-}" in
  "") powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${ps_script}" ;;
  --candidate) powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${ps_script}" -Candidate ;;
  -h|--help) echo "Usage: $0 [--candidate]" ;;
  *) echo "Usage: $0 [--candidate]" >&2; exit 2 ;;
esac
