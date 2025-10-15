FROM python:3.14 AS python-builder-base

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends swig
RUN curl  -o /tmp/lg.zip -L https://github.com/joan2937/lg/archive/refs/heads/master.zip \
    && unzip /tmp/lg.zip -d /tmp \
    && make -C /tmp/lg-master \
    && make -C /tmp/lg-master install \
    && PYPI=1 uvx --from build pyproject-build --installer uv --outdir /tmp/lgpio --wheel /tmp/lg-master/PY_LGPIO

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project --no-editable
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --all-extras
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv version --short > ./version.txt

RUN --mount=type=cache,target=/root/.cache/uv \
    find /tmp/lgpio -name '*.whl' -exec uv pip install lgpio@{} \;

FROM python:3.14-slim

WORKDIR /app
COPY --from=python-builder-base /app/.venv ./.venv
COPY --from=python-builder-base /app/version.txt ./version.txt

ENV PATH="/app/.venv/bin:$PATH"
ENV CONFIG="/app/config/conf.yaml"

ENTRYPOINT ["python", "-m", "qbee_gpio"]
