FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       git \
       ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/coolcode

COPY pyproject.toml README.md LICENSE ./
COPY coolcode ./coolcode

RUN python -m pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 coolcode \
    && mkdir -p /workspace /home/coolcode/.coolcode \
    && chown -R coolcode:coolcode /workspace /home/coolcode

ENV HOME=/home/coolcode

USER coolcode

WORKDIR /workspace

ENTRYPOINT ["coolcode"]
CMD ["--help"]
