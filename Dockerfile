FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "run_server.py"]

