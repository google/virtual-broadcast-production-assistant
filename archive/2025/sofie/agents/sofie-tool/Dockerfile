# Base
FROM --platform=$BUILDPLATFORM node:22-alpine AS base

WORKDIR /opt/sofie-tool

COPY package*.json ./

RUN npm ci --ignore-scripts
RUN npm rebuild

COPY . .

# Build
FROM base AS build

WORKDIR /opt/sofie-tool

RUN npm run build

# Production
FROM node:22-alpine

WORKDIR /opt/sofie-tool
COPY package*.json ./

ENV NODE_ENV=production
RUN npm ci --ignore-scripts
RUN npm rebuild

COPY --from=build /opt/sofie-tool/dist ./dist

EXPOSE 3000

USER node
CMD ["node", "."]
