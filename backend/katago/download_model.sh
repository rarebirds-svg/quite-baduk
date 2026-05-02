#!/bin/sh
# Fetches the two KataGo network files this app needs:
#   - main net  (kata1 b18c384nbt) — strong policy/value used for search
#   - human net (humanv0 b18c384nbt) — passed via -human-model for rank-targeted play
# Both are required for the strength.py humanSLProfile mapping to behave correctly.
#
# Skipping logic:
#   - If a file is already present and at least MIN_BYTES, we trust it (mounted
#     volumes preserve the model across container recreates).
#   - curl uses -f so HTTP 4xx/5xx fails loudly instead of writing the error
#     body as a 'model file' (a past bug — the 403 page was 111 bytes and broke
#     KataGo silently).
set -eu
MODEL_DIR=/katago/models
MAIN="$MODEL_DIR/kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"
HUMAN="$MODEL_DIR/b18c384nbt-humanv0.bin.gz"
MAIN_URL="https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"
HUMAN_URL="https://media.katagotraining.org/uploaded/networks/models/humanv0/b18c384nbt-humanv0.bin.gz"
MIN_BYTES=10485760  # 10 MB — anything smaller is almost certainly an error page.

mkdir -p "$MODEL_DIR"

if [ "${KATAGO_MOCK:-false}" = "true" ]; then
  echo "KATAGO_MOCK=true — skipping model downloads"
  exit 0
fi

# Drop obviously-broken stub files left by past failed downloads.
for f in "$MAIN" "$HUMAN"; do
  if [ -f "$f" ]; then
    sz=$(wc -c <"$f" | tr -d ' ')
    if [ "$sz" -lt "$MIN_BYTES" ]; then
      echo "WARN: $f is only $sz bytes — removing stub and re-attempting download."
      rm -f "$f"
    fi
  fi
done

fetch() {
  url="$1"; out="$2"; label="$3"
  echo "Downloading $label..."
  if ! curl -fL --retry 3 --connect-timeout 10 -o "$out" "$url"; then
    echo "ERROR: download failed: $url" >&2
    rm -f "$out"
    return 1
  fi
  echo "Downloaded: $out"
}

if [ ! -f "$MAIN" ]; then
  fetch "$MAIN_URL" "$MAIN" "KataGo main net (~98 MB)" || exit 1
fi

if [ ! -f "$HUMAN" ]; then
  if ! fetch "$HUMAN_URL" "$HUMAN" "KataGo Human-SL net (~99 MB)"; then
    cat >&2 <<'EOF'
ERROR: Human-SL net could not be downloaded automatically.
Mount or copy the file into the katago_models volume manually:

  docker run --rm -v baduk_katago_models:/dst -v /path/to/local:/src:ro \
    alpine cp /src/b18c384nbt-humanv0.bin.gz /dst/

Or set KATAGO_MOCK=true in the root .env to fall back to mock mode.
EOF
    exit 1
  fi
fi
