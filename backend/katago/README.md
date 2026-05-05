# KataGo

The backend talks to KataGo over GTP and expects the binary at
`bin/katago`. Two paths are supported on macOS — pick whichever fits.

## Apple Silicon (M-series), recommended: Homebrew + symlink

```bash
brew install katago
ln -sf /opt/homebrew/bin/katago bin/katago
```

The Homebrew bottle is built with `USE_BACKEND=METAL`, the same path the
production runbook expects. `bin/katago version` should report
`Using Metal backend`. First start performs a Metal tune (60–120 s,
cached at `~/.katago/`); subsequent starts are instant.

## From-source build (vendored)

```bash
./build_macos.sh
```

Clones KataGo `v1.16.4` into `vendor/KataGo`, runs cmake with
`-DUSE_BACKEND=METAL`, and copies the resulting binary to `bin/katago`.
Use this when you need a reproducible build pinned to a specific tag.

> Metal backend support landed in v1.16.x. Earlier tags (v1.15 and
> below) fail at the cmake configure step with
> `Unrecognized backend: METAL`. The script pins v1.16.4 for that reason.

If the Metal build fails on your Xcode toolchain, switch
`USE_BACKEND=METAL` to `USE_BACKEND=EIGEN` in the script. Eigen is
CPU-only — about 30× slower — but unblocks testing. Production must be
on Metal.

## Models

The Human-SL net `b18c384nbt-humanv0.bin.gz` is fetched once via
`./download_model.sh` and lives under `models/` (gitignored due to
size).
