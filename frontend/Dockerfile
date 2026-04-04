FROM cgr.dev/chainguard/node:latest-dev@sha256:6eec455f386d097fc57d8aa73bd06c27ab91faa4f02f9103f94b4c56e0f9a80b AS build
USER root

WORKDIR /app

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

# Use Corepack so pnpm is managed by Node, not a global npm install.
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

# Copy package manager files first for better Docker layer caching.
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* .npmrc* ./

# Clean install all node modules using pnpm with frozen lockfile.
RUN pnpm install --frozen-lockfile

# Copy source, then build the frontend assets.
COPY . .
RUN rm -f .env && pnpm run build

FROM gcr.io/distroless/nodejs22-debian12:nonroot@sha256:13593b7570658e8477de39e2f4a1dd25db2f836d68a0ba771251572d23bb4f8e AS external-website

# Metadata labels for the AdventureLog image
LABEL maintainer="Sean Morley" \
      version="v0.12.0" \
      description="AdventureLog - the ultimate self-hosted travel companion." \
      org.opencontainers.image.title="AdventureLog" \
      org.opencontainers.image.description="AdventureLog is a self-hosted travel companion that helps you plan, track, and share your adventures." \
      org.opencontainers.image.version="v0.12.0" \
      org.opencontainers.image.authors="Sean Morley" \
      org.opencontainers.image.url="https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/brand/banner.png" \
      org.opencontainers.image.source="https://github.com/seanmorley15/AdventureLog" \
      org.opencontainers.image.vendor="Sean Morley" \
      org.opencontainers.image.licenses="GPL-3.0"

WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app/build ./build
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json

EXPOSE 3000

# Distroless node image uses node as entrypoint.
CMD ["build/index.js"]
