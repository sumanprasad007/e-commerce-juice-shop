FROM node:22.22.3-bookworm-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init=1.2.5-* \
    && rm -rf /var/lib/apt/lists/*

FROM node:22.22.3-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    make \
    python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /juice-shop
COPY package*.json ./
COPY frontend/package*.json ./frontend/
RUN npm install --ignore-scripts --no-audit --no-fund
RUN cd frontend && npm install --ignore-scripts --no-audit --no-fund --legacy-peer-deps
COPY . .
RUN npm rebuild sqlite3 --build-from-source --foreground-scripts --no-audit --no-fund
RUN npm run build && npm prune --production
RUN npm rebuild sqlite3 --build-from-source --foreground-scripts --no-audit --no-fund \
    && find node_modules/sqlite3 -name 'node_sqlite3.node' -print -quit \
    && node -e "require('sqlite3'); console.log('sqlite3 native binding loaded after prune')"

FROM base AS production

ENV NODE_ENV=production
WORKDIR /juice-shop

COPY --from=builder --chown=node:node /juice-shop .

RUN mkdir -p logs && chown node:node logs

RUN node -e "require('sqlite3'); console.log('sqlite3 native binding loaded in runtime image')"

USER node
EXPOSE 3000
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "build/app.js"]
