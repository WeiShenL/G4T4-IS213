#!/bin/bash

# ===========================================
# FeastFinder Production Stop Script
# ===========================================

set -e

echo "=========================================="
echo "Stopping FeastFinder Production Services"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory (Root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Stop application services
echo -e "\n${YELLOW}Stopping production application services...${NC}"
cd "$SCRIPT_DIR"
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml down

# Stop Supabase
echo -e "\n${YELLOW}Stopping Supabase services...${NC}"
cd "$SCRIPT_DIR/backend/supabase"
docker compose down

echo -e "\n${GREEN}All production services stopped!${NC}"
