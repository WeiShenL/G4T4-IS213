# Stage 1: Build Vue static assets with Node.js
FROM node:20-alpine AS build-stage
WORKDIR /app

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Copy application code and build static bundle with placeholder environment tokens
COPY . .

ENV VITE_SUPABASE_URL=__VITE_SUPABASE_URL__
ENV VITE_SUPABASE_KEY=__VITE_SUPABASE_KEY__
ENV VITE_API_GATEWAY_URL=__VITE_API_GATEWAY_URL__
ENV VITE_STRIPE_PUBLISHABLE_KEY=__VITE_STRIPE_PUBLISHABLE_KEY__
ENV VITE_GOOGLE_MAPS_API_KEY=__VITE_GOOGLE_MAPS_API_KEY__

RUN npm run build

# Stage 2: Serve static files with Caddy (No Node.js runtime)
FROM caddy:2-alpine AS production-stage

# Copy Caddy configuration file
COPY Caddyfile /etc/caddy/Caddyfile

# Copy compiled static assets from build-stage
COPY --from=build-stage /app/dist /usr/share/caddy

# Copy runtime environment variable injection entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]

