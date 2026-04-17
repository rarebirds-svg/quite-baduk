#!/bin/sh
set -e
MODEL_DIR=/katago/models
MODEL="$MODEL_DIR/b18c384nbt-humanv0.bin.gz"
mkdir -p "$MODEL_DIR"
# Skip download when running in mock mode
if [ "${KATAGO_MOCK:-false}" = "true" ]; then
  echo "KATAGO_MOCK=true — skipping model download"
  exit 0
fi
if [ ! -f "$MODEL" ]; then
  echo "Downloading KataGo Human-SL model..."
  curl -L --retry 3 -o "$MODEL" \
    "https://media.katagotraining.org/uploaded/networks/models/humanv0/b18c384nbt-humanv0.bin.gz"
  echo "Model downloaded: $MODEL"
fi
