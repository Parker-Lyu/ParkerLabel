#!/usr/bin/env bash
set -euo pipefail

args=(--tag "$GITHUB_REF_NAME" --output release-assets)
if [ -d collected/macos-arm64 ]; then args+=(--macos collected/macos-arm64); fi
if [ -d collected/windows-x64 ]; then args+=(--windows collected/windows-x64); fi
python3 builds/prepare_release.py stage "${args[@]}"
(cd release-assets && sha256sum --check SHA256SUMS)

if gh release view "$GITHUB_REF_NAME" --json isDraft --jq .isDraft > draft-state.txt 2>/dev/null; then
  test "$(cat draft-state.txt)" = true
  gh release edit "$GITHUB_REF_NAME" --title "ParkerLabel $GITHUB_REF_NAME" --notes-file release-assets/release-notes.md
  asset_names="$(gh release view "$GITHUB_REF_NAME" --json assets --jq '.assets[].name')"
  for asset in \
    "ParkerLabel-${GITHUB_REF_NAME#v}-macos-arm64.zip" \
    "ParkerLabel-${GITHUB_REF_NAME#v}-windows-x64.zip" \
    build-info-macos-arm64.json build-info-windows-x64.json \
    license-inventory-macos-arm64.json license-inventory-windows-x64.json \
    size-report-macos-arm64.json size-report-windows-x64.json SHA256SUMS; do
    if printf '%s\n' "$asset_names" | grep -Fxq "$asset"; then
      gh release delete-asset "$GITHUB_REF_NAME" "$asset" --yes
    fi
  done
  gh release upload "$GITHUB_REF_NAME" release-assets/*.zip release-assets/*.json release-assets/SHA256SUMS --clobber
else
  gh release create "$GITHUB_REF_NAME" \
    release-assets/*.zip release-assets/*.json release-assets/SHA256SUMS \
    --draft --verify-tag \
    --title "ParkerLabel $GITHUB_REF_NAME" \
    --notes-file release-assets/release-notes.md
fi
test "$(gh release view "$GITHUB_REF_NAME" --json isDraft --jq .isDraft)" = true
