#!/bin/bash

# ===========================================
# FeastFinder Local Development Stop Script
# ===========================================

set -e

echo "=========================================="
echo "Stopping FeastFinder Services"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Stop application services
echo -e "\n${YELLOW}Stopping application services...${NC}"
cd "$SCRIPT_DIR"
docker compose down

# Stop Supabase
echo -e "\n${YELLOW}Stopping Supabase services...${NC}"
cd "$SCRIPT_DIR/supabase"
docker compose down

echo -e "\n${GREEN}All services stopped!${NC}"
echo ""
echo "To remove all data (fresh start), run:"
echo "  cd supabase && docker-compose down -v"
echo "  cd .. && docker-compose down -v"
