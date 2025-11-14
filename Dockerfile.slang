# syntax=docker/dockerfile:1.7
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-dev python3-setuptools \
    git curl wget build-essential \
    libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

ARG SGLANG_VERSION=0.4.2
RUN pip install --no-cache-dir \
    "sglang[srt]==${SGLANG_VERSION}" \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

EXPOSE 4084

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:4084/v1/models || exit 1

CMD ["python3", "-m", "sglang.launch_server", \
     "--model", "/local/grok-2", \
     "--tokenizer-path", "/local/grok-2/tokenizer.tok.json", \
     "--tp", "8", \
     "--quantization", "fp8", \
     "--attention-backend", "triton", \
     "--host", "0.0.0.0", \
     "--port", "30000"]

