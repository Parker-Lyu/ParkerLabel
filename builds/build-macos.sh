#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_prefix="${project_root}/builds/.env-macos-arm64"
generated_dir="${project_root}/builds/.generated"
work_dir="${project_root}/builds/.pyinstaller-work"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This build requires macOS arm64." >&2
  exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "Miniforge/Conda is required." >&2
  exit 1
fi

if [[ ! -x "${env_prefix}/bin/python" ]]; then
  conda create --yes --prefix "${env_prefix}" \
    python=3.11.16 \
    pip=26.0.1 \
    packaging=26.3 \
    setuptools=84.0.0 \
    wheel=0.48.0
fi

"${env_prefix}/bin/python" -m pip install \
  --disable-pip-version-check \
  --requirement "${project_root}/builds/requirements-macos-arm64.lock"

version="$("${env_prefix}/bin/python" -c "from parker_label_app.app_info import APP_VERSION; print(APP_VERSION or 'dev')")"
if [[ "${version}" != "dev" ]]; then
  if [[ -n "$(git -C "${project_root}" status --short)" ]]; then
    echo "Release builds require a clean worktree." >&2
    exit 1
  fi
  if [[ "$(git -C "${project_root}" tag --points-at HEAD)" != "v${version}" ]]; then
    echo "Release builds require HEAD to have tag v${version}." >&2
    exit 1
  fi
fi
output_dir="${project_root}/builds/output/${version}/macos-arm64"
stage_dir="${work_dir}/dist"
archive="${output_dir}/ParkerLabel-${version}-macos-arm64.zip"

rm -rf "${generated_dir}" "${work_dir}" "${output_dir}"
mkdir -p "${generated_dir}" "${work_dir}" "${output_dir}"

"${env_prefix}/bin/python" "${project_root}/builds/write_build_info.py" \
  --project-root "${project_root}" \
  --output "${generated_dir}/build-info.json"

PARKER_LABEL_VERSION="${version}" "${env_prefix}/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --distpath "${stage_dir}" \
  --workpath "${work_dir}/build" \
  "${project_root}/builds/ParkerLabel.spec"

mv "${stage_dir}/ParkerLabel.app" "${output_dir}/ParkerLabel.app"
"${env_prefix}/bin/python" "${project_root}/builds/prune_macos_bundle.py" \
  "${output_dir}/ParkerLabel.app"
codesign --force --deep --sign - "${output_dir}/ParkerLabel.app"
ditto -c -k --sequesterRsrc --keepParent "${output_dir}/ParkerLabel.app" "${archive}"

cp "${generated_dir}/build-info.json" "${output_dir}/build-info.json"
(
  cd "${output_dir}"
  shasum -a 256 "$(basename "${archive}")" > SHA256SUMS
)

"${env_prefix}/bin/python" "${project_root}/builds/measure_bundle.py" \
  --app "${output_dir}/ParkerLabel.app" \
  --archive "${archive}" \
  --manifest "${project_root}/model-bundle.json" \
  --configs "${output_dir}/configs" \
  --output "${output_dir}/size-report.json"
