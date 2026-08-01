#!/bin/sh
set -e

# Replace placeholders inside all static JS files with live VPS environment variables
echo "Injecting VPS environment variables into static JS bundle..."

find /usr/share/caddy -type f -name "*.js" | while read -r file; do
  if [ -f "$file" ]; then
    [ -n "$VITE_SUPABASE_URL" ] && sed -i "s|__VITE_SUPABASE_URL__|${VITE_SUPABASE_URL}|g" "$file"
    [ -n "$VITE_SUPABASE_KEY" ] && sed -i "s|__VITE_SUPABASE_KEY__|${VITE_SUPABASE_KEY}|g" "$file"
    [ -n "$VITE_API_GATEWAY_URL" ] && sed -i "s|__VITE_API_GATEWAY_URL__|${VITE_API_GATEWAY_URL}|g" "$file"
    [ -n "$VITE_STRIPE_PUBLISHABLE_KEY" ] && sed -i "s|__VITE_STRIPE_PUBLISHABLE_KEY__|${VITE_STRIPE_PUBLISHABLE_KEY}|g" "$file"
    [ -n "$VITE_GOOGLE_MAPS_API_KEY" ] && sed -i "s|__VITE_GOOGLE_MAPS_API_KEY__|${VITE_GOOGLE_MAPS_API_KEY}|g" "$file"
    # Any `[ -n "$VAR" ] && sed` above returns non-zero when VAR is unset. That
    # status becomes the loop's, propagates out of the pipeline subshell, and
    # `set -e` then kills this script before `exec caddy run` below. Anchoring
    # the body with a success keeps one missing env var from bricking boot.
    true
  fi
done

echo "Starting Caddy server..."
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
