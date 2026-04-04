# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./

FROM base AS deps
RUN npm ci

FROM deps AS build
COPY tsconfig.json tsconfig.server.json webpack.config.js server.ts ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM base AS runtime-deps
RUN npm ci --omit=dev

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=runtime-deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/dist-server ./dist-server
COPY package.json ./package.json
EXPOSE 3000
CMD ["node", "dist-server/server.js"]

FROM deps AS development
COPY tsconfig.json tsconfig.server.json webpack.config.js server.ts ./
COPY src ./src
COPY public ./public
EXPOSE 3000 8080
CMD ["sh", "-c", "npx concurrently \"webpack serve --host 0.0.0.0 --port 8080 --hot\" \"npx tsc -p tsconfig.server.json --watch\" \"sh -c 'until [ -f dist-server/server.js ]; do sleep 1; done; node --watch dist-server/server.js'\""]
