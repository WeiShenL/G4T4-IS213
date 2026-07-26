# Stage 1: Build Vue static assets with Node.js
FROM node:20-alpine AS build-stage
WORKDIR /app

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Copy application code and build static bundle
COPY . .
RUN npm run build

# Stage 2: Serve static files with Caddy (No Node.js runtime)
FROM caddy:2-alpine AS production-stage

# Copy Caddy configuration file
COPY Caddyfile /etc/caddy/Caddyfile

# Copy compiled static assets from build-stage
COPY --from=build-stage /app/dist /usr/share/caddy

EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
