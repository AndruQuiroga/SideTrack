# syntax=docker/dockerfile:1
FROM node:20-bullseye AS builder

ENV PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH" \
    NODE_ENV=development
RUN corepack enable

WORKDIR /app

# Copy workspace metadata
COPY package.json pnpm-workspace.yaml tsconfig.base.json ./
COPY apps ./apps
COPY packages ./packages

# Install dependencies and build the web bundle and its deps
RUN pnpm install --ignore-scripts --frozen-lockfile=false \
  && pnpm --filter @sidetrack/web... run build \
  && pnpm prune --prod

FROM node:20-bullseye-slim
ENV NODE_ENV=production \
    PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

# Copy only the built workspace artifacts
COPY --from=builder /app /app

EXPOSE 3000
CMD ["node", "apps/web/dist/index.js"]
