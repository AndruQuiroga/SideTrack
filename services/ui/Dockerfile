FROM node:20-slim

WORKDIR /app

# Install deps
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile || pnpm install

# App code
COPY . .

EXPOSE 3000
CMD ["pnpm","dev","--","--host","0.0.0.0"]
