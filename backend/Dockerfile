FROM python:3.11-slim-bullseye AS base
WORKDIR /app

# KataGo's published Linux binary needs libzip.so.5 + libssl.so.1.1.
# bullseye ships libzip4 + libssl1.1 — the libzip ABI between 4 and 5
# is forward-compatible for the read-only model-loading the binary
# needs, so symlink .so.4 → .so.5 to satisfy the dynamic linker.
RUN apt-get update && apt-get install -y --no-install-recommends \
        unzip curl libgomp1 libzip4 libssl1.1 \
    && ln -s /usr/lib/x86_64-linux-gnu/libzip.so.4 /usr/lib/x86_64-linux-gnu/libzip.so.5 \
    && rm -rf /var/lib/apt/lists/*

# Install KataGo (Eigen CPU build — no GPU required)
ARG KATAGO_VER=1.15.3
RUN curl -L -o /tmp/katago.zip \
      "https://github.com/lightvector/KataGo/releases/download/v${KATAGO_VER}/katago-v${KATAGO_VER}-eigen-linux-x64.zip" \
    && unzip /tmp/katago.zip -d /tmp/katago \
    && mv /tmp/katago/katago /usr/local/bin/katago \
    && chmod +x /usr/local/bin/katago \
    && rm -rf /tmp/katago /tmp/katago.zip

# KataGo model download (skipped when KATAGO_MOCK=true)
COPY katago/download_model.sh /usr/local/bin/download_model.sh
RUN chmod +x /usr/local/bin/download_model.sh

COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .

COPY . /app/
RUN mkdir -p /data /katago/models
COPY katago/config.cfg /katago/config.cfg

EXPOSE 8000
# alembic upgrade is idempotent: running on an already-current DB is a
# no-op, so it's safe to run on every container start. Catches the case
# where a fresh volume comes up empty.
CMD ["sh", "-c", "/usr/local/bin/download_model.sh && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
