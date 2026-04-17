FROM python:3.11-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip curl libgomp1 && rm -rf /var/lib/apt/lists/*

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
CMD ["sh", "-c", "/usr/local/bin/download_model.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
