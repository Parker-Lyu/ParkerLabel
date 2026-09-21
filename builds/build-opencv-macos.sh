#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_env="${project_root}/builds/.env-opencv-macos-arm64"
source_dir="${project_root}/builds/.opencv-python-src"
wheelhouse="${project_root}/builds/.opencv-wheelhouse"
target_python="${1:-${project_root}/builds/.env-macos-arm64/bin/python}"
opencv_python_commit="b83046cda41133f1bf2e73e99dba16a1248f103a"
opencv_commit="40738fb16ceddb5fb3fea747585f7ce6abb0605b"
wheel="${wheelhouse}/opencv_python_headless-5.0.0.93-cp37-abi3-macosx_11_0_arm64.whl"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This build requires macOS arm64." >&2
  exit 1
fi

if [[ ! -x "${target_python}" ]]; then
  echo "Target Python does not exist: ${target_python}" >&2
  exit 1
fi

if [[ ! -x "${build_env}/bin/python" ]]; then
  conda create --yes --prefix "${build_env}" python=3.11.16 pip=26.0.1
fi

"${build_env}/bin/python" -m pip install \
  --disable-pip-version-check \
  cmake==3.31.10 \
  ninja==1.13.2 \
  numpy==2.0.2 \
  packaging==26.3 \
  scikit-build==0.18.1 \
  setuptools==69.5.1 \
  wheel==0.48.0

if [[ ! -f "${wheel}" ]]; then
  rm -rf "${source_dir}"
  git init "${source_dir}"
  git -C "${source_dir}" remote add origin https://github.com/opencv/opencv-python.git
  git -C "${source_dir}" fetch --depth 1 origin "${opencv_python_commit}"
  git -C "${source_dir}" checkout --detach FETCH_HEAD
  git -C "${source_dir}" submodule update --init --depth 1 opencv

  if [[ "$(git -C "${source_dir}" rev-parse HEAD)" != "${opencv_python_commit}" ]]; then
    echo "Unexpected opencv-python source revision." >&2
    exit 1
  fi
  if [[ "$(git -C "${source_dir}/opencv" rev-parse HEAD)" != "${opencv_commit}" ]]; then
    echo "Unexpected OpenCV source revision." >&2
    exit 1
  fi
  git -C "${source_dir}" tag 93
  git -C "${source_dir}" apply "${project_root}/builds/opencv-python-minimal.patch"

  cmake_args=(
    -DCMAKE_BUILD_TYPE=Release
    -DCMAKE_OSX_ARCHITECTURES=arm64
    -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0
    -DBUILD_LIST=core,imgproc,imgcodecs,python3
    -DBUILD_JPEG=ON
    -DBUILD_OPENEXR=OFF
    -DBUILD_PNG=ON
    -DBUILD_ZLIB=ON
    -DBUILD_opencv_apps=OFF
    -DBUILD_opencv_java=OFF
    -DBUILD_opencv_js=OFF
    -DBUILD_opencv_objc=OFF
    -DBUILD_opencv_python_tests=OFF
    -DBUILD_opencv_world=OFF
    -DBUILD_SHARED_LIBS=OFF
    -DBUILD_DOCS=OFF
    -DBUILD_EXAMPLES=OFF
    -DBUILD_PERF_TESTS=OFF
    -DBUILD_TESTS=OFF
    -DINSTALL_C_EXAMPLES=OFF
    -DINSTALL_PYTHON_EXAMPLES=OFF
    -DOPENCV_ENABLE_NONFREE=OFF
    -DOPENCV_GENERATE_PKGCONFIG=OFF
    -DWITH_1394=OFF
    -DWITH_ADE=OFF
    -DWITH_AVFOUNDATION=OFF
    -DWITH_AVIF=OFF
    -DWITH_EIGEN=OFF
    -DWITH_FFMPEG=OFF
    -DWITH_GDAL=OFF
    -DWITH_GDCM=OFF
    -DWITH_GSTREAMER=OFF
    -DWITH_IMGCODEC_HDR=OFF
    -DWITH_IMGCODEC_GIF=OFF
    -DWITH_IMGCODEC_PFM=OFF
    -DWITH_IMGCODEC_PXM=OFF
    -DWITH_IMGCODEC_SUNRASTER=OFF
    -DWITH_JASPER=OFF
    -DWITH_JPEGXL=OFF
    -DWITH_ITT=OFF
    -DWITH_LAPACK=OFF
    -DWITH_OPENCL=OFF
    -DWITH_OPENEXR=OFF
    -DWITH_OPENJPEG=OFF
    -DWITH_PROTOBUF=OFF
    -DWITH_QUIRC=OFF
    -DWITH_TIFF=OFF
    -DWITH_VTK=OFF
    -DWITH_WEBP=OFF
  )
  mkdir -p "${wheelhouse}"
  (
    cd "${source_dir}"
    export CMAKE_ARGS="${cmake_args[*]}"
    export CMAKE_BUILD_PARALLEL_LEVEL="$(sysctl -n hw.logicalcpu)"
    export ENABLE_CONTRIB=0
    export ENABLE_HEADLESS=1
    export MACOSX_DEPLOYMENT_TARGET=11.0
    "${build_env}/bin/python" setup.py bdist_wheel \
      --py-limited-api=cp37 \
      --dist-dir "${wheelhouse}"
  )
fi

"${target_python}" -m zipfile -t "${wheel}"
"${target_python}" -m pip uninstall --yes \
  opencv-contrib-python \
  opencv-contrib-python-headless \
  opencv-python \
  opencv-python-headless >/dev/null 2>&1 || true
"${target_python}" -m pip install \
  --disable-pip-version-check \
  --force-reinstall \
  --no-deps \
  "${wheel}"
