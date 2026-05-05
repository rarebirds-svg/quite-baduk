#!/usr/bin/env bash
# Build KataGo with the Metal backend on Apple Silicon.
#
# This is the from-source path for vendored builds (and matches what the
# Homebrew bottle does internally). For most contributors `brew install
# katago` followed by `ln -s /opt/homebrew/bin/katago bin/katago`
# is the fastest way to get a Metal-accelerated binary — see README.md.
#
# Idempotent: skips clone if vendor/KataGo exists; skips mkdir build if
# the build directory exists.
set -euo pipefail

# Metal backend support landed in KataGo v1.16.x — older tags (v1.15 and
# below) fail at the cmake configure step with "Unrecognized backend: METAL".
KATAGO_VERSION="v1.16.4"
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
