FROM python:3.14 AS lgpio-builder

RUN apt-get update && apt-get install -y --no-install-recommends swig

WORKDIR /build
RUN --mount=from=ghcr.io/astral-sh/uv:0.9,source=/uv,target=/bin/uv \
    --mount=from=ghcr.io/astral-sh/uv:0.9,source=/uvx,target=/bin/uvx \
    curl -o lg.zip -L https://github.com/joan2937/lg/archive/refs/heads/master.zip \
    && unzip lg.zip -d . \
    && make -C lg-master \
    && make -C lg-master install \
    && PYPI=1 uvx --from build pyproject-build --installer uv --outdir /wheels --wheel lg-master/PY_LGPIO

FROM python:3.14-slim

WORKDIR /app
RUN --mount=from=ghcr.io/astral-sh/uv:0.9,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=qbee_gpio,target=qbee_gpio \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --frozen --no-dev --no-editable --compile-bytecode
RUN --mount=from=ghcr.io/astral-sh/uv:0.9,source=/uv,target=/bin/uv \
    --mount=from=lgpio-builder,source=/wheels,target=/wheels \
    find /wheels -name '*.whl' -exec uv pip install --compile-bytecode lgpio@{} \;

ENV PATH="/app/.venv/bin:$PATH"
ENV CONFIG="/app/config/conf.yaml"

ENTRYPOINT ["python", "-m", "qbee_gpio"]
