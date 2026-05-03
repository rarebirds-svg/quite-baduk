# KataGo

## Apple Silicon (M-series) production build

```bash
./build_macos.sh
```

Produces `bin/katago` linked against Metal. First start performs a
GPU benchmark/tune (60–120s, cached at `~/.katago/`). Subsequent
starts are instant.

If the Metal build fails on your Xcode toolchain (cmake error about
the Metal framework), switch `USE_BACKEND=METAL` to `USE_BACKEND=EIGEN`
in the script. Eigen is CPU-only — about 30× slower — but unblocks
testing. Production must be on Metal.
