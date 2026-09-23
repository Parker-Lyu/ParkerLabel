#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_prefix="${project_root}/builds/.env-macos-arm64"
generated_dir="${project_root}/builds/.generated"
work_dir="${project_root}/builds/.pyinstaller-work"
candidate_build=false

case "${1:-}" in
  "")
    ;;
  --candidate)
    candidate_build=true
    ;;
  -h|--help)
    echo "Usage: $0 [--candidate]"
    exit 0
    ;;
  *)
    echo "Usage: $0 [--candidate]" >&2
    exit 2
    ;;
esac

if [[ "$#" -gt 1 ]]; then
  echo "Usage: $0 [--candidate]" >&2
  exit 2
fi

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This build requires macOS arm64." >&2
  exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "Miniforge/Conda is required." >&2
  exit 1
fi

conda_base="$(conda info --base)"
version="$("${conda_base}/bin/python" -c 'import runpy, sys; print(runpy.run_path(sys.argv[1])["APP_VERSION"] or "dev")' "${project_root}/parker_label_app/app_info.py")"
build_type="development"
artifact_version="${version}"
if [[ "${candidate_build}" == true ]]; then
  if [[ "${version}" == "dev" ]]; then
    echo "Candidate builds require APP_VERSION to be set." >&2
    exit 1
  fi
  if [[ -n "$(git -C "${project_root}" status --short)" ]]; then
    echo "Candidate builds require a clean worktree." >&2
    exit 1
  fi
  build_type="candidate"
  artifact_version="${version}-candidate"
elif [[ "${version}" != "dev" ]]; then
  if [[ -n "$(git -C "${project_root}" status --short)" ]]; then
    echo "Release builds require a clean worktree." >&2
    exit 1
  fi
  if [[ "$(git -C "${project_root}" tag --points-at HEAD)" != "v${version}" ]]; then
    echo "Release builds require HEAD to have tag v${version}." >&2
    exit 1
  fi
  build_type="release"
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

"${project_root}/builds/build-opencv-macos.sh" "${env_prefix}/bin/python"
"${env_prefix}/bin/python" "${project_root}/builds/verify_opencv_runtime.py"
"${env_prefix}/bin/python" -m unittest discover \
  --start-directory "${project_root}/tests" \
  --pattern "test_*.py"

output_dir="${project_root}/builds/output/${artifact_version}/macos-arm64"
stage_dir="${work_dir}/dist"
package_dir="${work_dir}/package"
archive_directory_name="ParkerLabel-${version}"
archive_root="${package_dir}/${archive_directory_name}"
archive="${output_dir}/ParkerLabel-${artifact_version}-macos-arm64.zip"

rm -rf "${generated_dir}" "${work_dir}"
mkdir -p "${generated_dir}" "${work_dir}" "${output_dir}"
rm -rf \
  "${output_dir}/ParkerLabel.app" \
  "${output_dir}/configs"
rm -f \
  "${archive}" \
  "${output_dir}/build-info.json" \
  "${output_dir}/license-inventory.json" \
  "${output_dir}/SHA256SUMS" \
  "${output_dir}/size-report.json"

"${env_prefix}/bin/python" "${project_root}/builds/write_build_info.py" \
  --project-root "${project_root}" \
  --build-type "${build_type}" \
  --output "${generated_dir}/build-info.json"
"${env_prefix}/bin/python" "${project_root}/builds/stage_licenses.py" \
  --source "${project_root}/third_party_licenses" \
  --inventory "${project_root}/third_party_licenses/macos-arm64-inventory.json" \
  --output "${generated_dir}/third_party_licenses"

PARKER_LABEL_VERSION="${version}" "${env_prefix}/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --distpath "${stage_dir}" \
  --workpath "${work_dir}/build" \
  "${project_root}/builds/ParkerLabel.spec"

mv "${stage_dir}/ParkerLabel.app" "${output_dir}/ParkerLabel.app"
"${env_prefix}/bin/python" "${project_root}/builds/prune_macos_bundle.py" \
  "${output_dir}/ParkerLabel.app"
"${env_prefix}/bin/python" "${project_root}/builds/audit_macos_licenses.py" \
  --app "${output_dir}/ParkerLabel.app" \
  --expected "${project_root}/third_party_licenses/macos-arm64-inventory.json" \
  --report "${output_dir}/license-inventory.json"
codesign --force --deep --sign - "${output_dir}/ParkerLabel.app"
codesign --verify --deep --strict --verbose=2 "${output_dir}/ParkerLabel.app"
mkdir -p "${archive_root}"
ditto "${output_dir}/ParkerLabel.app" "${archive_root}/ParkerLabel.app"
ditto -c -k --sequesterRsrc --keepParent "${archive_root}" "${archive}"
unzip -tq "${archive}"

verification_dir="$(mktemp -d)"
trap 'rm -rf "${verification_dir}"' EXIT
ditto -x -k "${archive}" "${verification_dir}"
codesign --verify --deep --strict --verbose=2 \
  "${verification_dir}/${archive_directory_name}/ParkerLabel.app"

cp "${generated_dir}/build-info.json" "${output_dir}/build-info.json"
(
  cd "${output_dir}"
  shasum -a 256 "$(basename "${archive}")" > SHA256SUMS
  shasum -a 256 -c SHA256SUMS
)

"${env_prefix}/bin/python" "${project_root}/builds/measure_bundle.py" \
  --app "${output_dir}/ParkerLabel.app" \
  --archive "${archive}" \
  --manifest "${project_root}/model-bundle.json" \
  --configs "${output_dir}/configs" \
  --output "${output_dir}/size-report.json"
