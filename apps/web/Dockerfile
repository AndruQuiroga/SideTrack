# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS base

ENV PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

FROM base AS deps
ENV NODE_ENV=development
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/bot/package.json apps/bot/package.json
COPY packages/api-client/package.json packages/api-client/package.json

RUN pnpm install --ignore-scripts --frozen-lockfile

FROM deps AS build
# Inlined into the browser bundle at build time: the public API origin.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
COPY . .
RUN pnpm --filter @sidetrack/web... run build \
  && pnpm prune --prod

FROM node:22-bookworm-slim AS runner
ENV NODE_ENV=production \
    PNPM_HOME=/root/.local/share/pnpm \
    PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app

COPY --from=build /app /app

EXPOSE 3000
CMD ["pnpm", "--filter", "@sidetrack/web", "exec", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
