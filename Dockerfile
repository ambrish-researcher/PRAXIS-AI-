# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci; else npm ci; fi
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock backend/requirements.lock
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r backend/requirements.lock; else pip install --no-cache-dir -r backend/requirements.lock; fi
COPY backend/ backend/
COPY --from=web /app/frontend/dist frontend/dist
RUN chmod -R a+rX /app/backend /app/frontend && groupadd --gid 10001 praxis && useradd --uid 10001 --gid praxis --no-create-home praxis && mkdir -p /var/data/praxis && chown -R praxis:praxis /var/data
ENV PRAXIS_DATA_DIR=/var/data/praxis PRAXIS_SERVE_WEB=1 PRAXIS_REQUIRE_AUTH=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["python", "backend/praxis/container_start.py"]
