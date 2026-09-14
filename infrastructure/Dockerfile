FROM node:22.22.3-bookworm-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init=1.2.5-* \
    && rm -rf /var/lib/apt/lists/*

FROM node:22.22.3-bookworm AS builder

WORKDIR /juice-shop
COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install --ignore-scripts --no-audit --no-fund --legacy-peer-deps
COPY . .
RUN npm run build && npm prune --production

FROM base AS production

ENV NODE_ENV=production
WORKDIR /juice-shop

COPY --from=builder --chown=node:node /juice-shop .

USER node
EXPOSE 3000
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "build/app.js"]
