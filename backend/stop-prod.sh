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

echo -e "\n${GREEN}All production services stopped!${NC}"
