#!/bin/bash

# ===========================================
# FeastFinder Production Startup Script
# ===========================================
# This script starts all services in Production Hardened Mode (Caddy Frontend + Network Port Lockdown)
# ===========================================

set -e

echo "=========================================="
echo "FeastFinder Production Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Get script directory (Root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Step 1: Setup environment files if they don't exist
echo -e "\n${YELLOW}Step 1: Checking environment files...${NC}"

if [ ! -f "$SCRIPT_DIR/backend/supabase/.env" ]; then
    echo "Creating backend/supabase/.env from template..."
    cp "$SCRIPT_DIR/backend/supabase/.env.example" "$SCRIPT_DIR/backend/supabase/.env"
fi

if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "Creating backend .env from template..."
    cp "$SCRIPT_DIR/backend/.env.example" "$SCRIPT_DIR/backend/.env"
fi

if [ ! -f "$SCRIPT_DIR/frontend/.env" ]; then
    echo "Creating frontend .env from template..."
    cp "$SCRIPT_DIR/frontend/.env.example" "$SCRIPT_DIR/frontend/.env"
fi

echo -e "${GREEN}Environment files ready!${NC}"

# Step 2: Start Supabase
echo -e "\n${YELLOW}Step 2: Starting Supabase services...${NC}"
cd "$SCRIPT_DIR/backend/supabase"
docker compose up -d

# Wait for Supabase to be healthy
echo "Waiting for Supabase database to be ready..."
until docker exec supabase-db pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e "\n${GREEN}Supabase database is ready!${NC}"

# Wait a bit more for all services to initialize
echo "Waiting for Supabase services to initialize..."
sleep 10

# Step 2.5: Wait for supabase-auth (GoTrue) to finish its migrations
echo -e "\n${YELLOW}Step 2.5: Waiting for Supabase Auth to initialize auth schema...${NC}"
until docker exec supabase-auth sh -c 'wget -qO- http://localhost:9999/health 2>/dev/null | grep -q "version"' 2>/dev/null; do
    echo -n "."
    sleep 3
done
echo -e "\n${GREEN}Supabase Auth is ready!${NC}"

echo "Applying app schema (depends on auth.users existing)..."
for f in 01-schema.sql 02-triggers.sql 03-seed-data.sql 04-rls-policies.sql; do
    echo "  -> $f"
    docker exec -i supabase-db psql -v ON_ERROR_STOP=1 -U postgres -d postgres < "$SCRIPT_DIR/backend/supabase/init/app-schema/$f" > /dev/null
done
echo -e "${GREEN}App schema applied!${NC}"

echo "Granting Studio access to auth schema..."
docker exec supabase-db psql -U postgres -d postgres -c "
GRANT USAGE ON SCHEMA auth TO supabase_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA auth TO supabase_admin;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA auth TO supabase_admin;
" > /dev/null && echo -e "${GREEN}Studio permissions applied!${NC}"

echo "Reloading PostgREST schema cache..."
docker exec supabase-db psql -U postgres -d postgres -c "NOTIFY pgrst, 'reload schema';" > /dev/null && echo -e "${GREEN}PostgREST cache reloaded!${NC}"

# Step 3: Start application services with production overrides
echo -e "\n${YELLOW}Step 3: Starting FeastFinder application services (Production Mode)...${NC}"
cd "$SCRIPT_DIR"
docker compose -f docker-compose.yaml -f backend/docker-compose.prod.yml up -d --build

echo -e "\n${GREEN}=========================================="
echo "All production services started successfully!"
echo "==========================================${NC}"
echo ""
echo "Access points:"
echo "  - Production Caddy Frontend: http://localhost:8080"
echo "  - Public API Gateway:        http://localhost:8000"
echo "  - Localhost Admin UIs (SSH Tunnel only):"
echo "      * Kong Admin:       http://localhost:8001"
echo "      * Kong Manager:     http://localhost:8002"
echo "      * RabbitMQ Console: http://localhost:15672"
echo ""
echo "To view logs:"
echo "  docker compose logs -f [service-name]"
echo ""
echo "To stop all services:"
echo "  ./stop-prod.sh"
