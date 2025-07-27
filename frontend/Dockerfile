# ----------------------
# Stage 1: Build the app
# ----------------------
FROM docker.io/node:22-alpine AS builder

ARG GIT_SHA=unknown
ARG GIT_TAG=latest
ARG BUILD_DATE=unknown

# Set working directory
WORKDIR /app

COPY . ./
# Install pnpm globally
RUN npm install -g pnpm && \
    pnpm install --frozen-lockfile && \
    rm -f .env && \
    pnpm run build && \
    mv /app/package.json /app/build/package.json;\
    ls -lah .; \
    ls -lah ./build

# ----------------------------
# Stage 2: Install Production Dependencies
# ----------------------------
FROM docker.io/node:22-alpine AS deps

WORKDIR /app
COPY --from=builder /app/build/package.json ./
RUN npm install --omit=dev && \
    addgroup -g 349 adventurelog && \
    adduser -D -u 349 -G adventurelog adventurelog && \
    chown -R 349:349 /app

# ----------------------------
# Stage 3: Distroless Runtime
# ----------------------------
FROM gcr.io/distroless/nodejs20

LABEL maintainer="Sean Morley" \
      org.opencontainers.image.title="AdventureLog" \
      org.opencontainers.image.description="AdventureLog is a self-hosted travel companion that helps you plan, track, and share your adventures." \
      org.opencontainers.image.authors="Sean Morley" \
      org.opencontainers.image.url="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/banner.png" \
      org.opencontainers.image.source="https://github.com/seanmorley15/AdventureLog" \
      org.opencontainers.image.vendor="Sean Morley" \
      org.opencontainers.image.version="${GIT_TAG}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="GPL-3.0"

USER 349:349
WORKDIR /app

COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group
COPY --from=builder /app/build ./
COPY --from=deps /app/node_modules ./node_modules

CMD ["index.js"]

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD /nodejs/bin/node -e "require('net').connect(3000).on('connect', () => process.exit(0)).on('error', () => process.exit(1))"