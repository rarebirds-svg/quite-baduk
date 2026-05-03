#!/usr/bin/env bash
# Build KataGo with Metal backend on Apple Silicon. Idempotent: checks
# out a fresh clone into `vendor/KataGo` if missing, then re-runs cmake
# only when the build/ directory is absent.
set -euo pipefail

KATAGO_VERSION="v1.15.3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="${SCRIPT_DIR}/vendor"
SRC="${VENDOR}/KataGo"
BIN_OUT="${SCRIPT_DIR}/bin/katago"

mkdir -p "${VENDOR}" "${SCRIPT_DIR}/bin"

if [ ! -d "${SRC}" ]; then
  git clone --depth 1 --branch "${KATAGO_VERSION}" \
    https://github.com/lightvector/KataGo.git "${SRC}"
fi

cd "${SRC}/cpp"
if [ ! -d build ]; then
  mkdir build
fi
cd build
cmake -DUSE_BACKEND=METAL -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --parallel "$(sysctl -n hw.ncpu)"

cp katago "${BIN_OUT}"
echo "OK: built ${BIN_OUT}"
"${BIN_OUT}" version
