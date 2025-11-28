# syntax=docker/dockerfile:1
FROM node:20-bookworm-slim AS base

ENV PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

FROM base AS deps
ENV NODE_ENV=development
COPY package.json pnpm-workspace.yaml tsconfig.base.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/bot/package.json apps/bot/package.json
COPY apps/worker/package.json apps/worker/package.json
COPY packages/shared/package.json packages/shared/package.json

RUN pnpm install --ignore-scripts --frozen-lockfile=false

FROM deps AS build
ENV NODE_ENV=production
COPY . .
RUN pnpm --filter @sidetrack/web... run build \
  && pnpm prune --prod

FROM node:20-bookworm-slim AS runner
ENV NODE_ENV=production \
    PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

COPY --from=build /app /app

EXPOSE 3000
CMD ["pnpm", "--filter", "@sidetrack/web", "exec", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
