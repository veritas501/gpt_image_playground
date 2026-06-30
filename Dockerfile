FROM oven/bun:1 AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ ./
RUN bun run build

FROM python:3.12-slim AS runtime

ENV IMAGE2_GEN_CONFIG=/config/config.toml \
    IMAGE2_GEN_DB_PATH=/data/app.db \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /build/frontend/dist /app/frontend/dist

RUN mkdir -p /config /data/images

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host \"${HOST}\" --port \"${PORT}\""]
