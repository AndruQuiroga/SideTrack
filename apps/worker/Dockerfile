# syntax=docker/dockerfile:1
FROM node:20-bullseye AS builder

ENV PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH" \
    NODE_ENV=development
RUN corepack enable

WORKDIR /app

COPY package.json pnpm-workspace.yaml tsconfig.base.json ./
COPY apps ./apps
COPY packages ./packages

RUN pnpm install --ignore-scripts --frozen-lockfile=false \
  && pnpm --filter @sidetrack/worker... run build \
  && pnpm prune --prod

FROM node:20-bullseye-slim
ENV NODE_ENV=production \
    PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

COPY --from=builder /app /app

CMD ["node", "apps/worker/dist/index.js"]
