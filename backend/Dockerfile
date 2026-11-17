# Imagem única do backend: o compose escolhe o comando de cada serviço.
FROM ghcr.io/astral-sh/uv:0.13.7-python3.12-trixie-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependências antes do código, para o cache da camada sobreviver a mudanças em src/.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
