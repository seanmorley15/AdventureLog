# Development image for AdventureLog: Django/GeoDjango backend + SvelteKit frontend.
# Versions mirror docker/Dockerfile (Python 3.13, Node 22, pnpm 10.32).
FROM node:22-bookworm-slim AS node-runtime

FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

ARG PNPM_VERSION=10.32.1

# GDAL for django.contrib.gis, psql for the entrypoint helpers, memcached for
# Django's cache (settings expect it on 127.0.0.1:11211), fonts for PDF export.
# The base image ships a yarn apt source whose signing key has expired and breaks
# `apt-get update`; we don't use yarn, so drop it.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        build-essential \
        fonts-noto-core \
        gdal-bin \
        libgdal-dev \
        memcached \
        postgresql-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Node from the official image (same approach as the production image).
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npm install -g "pnpm@${PNPM_VERSION}"

USER vscode
