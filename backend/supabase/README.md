# Local Supabase Setup for FeastFinder

This directory contains the configuration for running Supabase locally using Docker.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB of RAM available for Docker

## Quick Start

### 1. Set up environment variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit if needed (defaults work for local development)
```

### 2. Start Supabase

```bash
# From this directory (backend/supabase)
docker-compose up -d
```

### 3. Verify Supabase is running

- **Supabase Studio (Dashboard)**: http://localhost:3000
- **Supabase API**: http://localhost:8100
- **PostgreSQL**: localhost:5433

### 4. Start the application stack

```bash
# From the backend directory
cd ..
docker-compose up -d
```

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| supabase-db | 5433 | PostgreSQL database |
| supabase-kong | 8100 | API Gateway (routes to auth/rest) |
| supabase-auth | - | GoTrue authentication service |
| supabase-rest | - | PostgREST API |
| supabase-studio | 3000 | Web dashboard |
| supabase-meta | - | Database metadata API |

## Default Credentials

### Database
- **Host**: localhost
- **Port**: 5433
- **User**: postgres
- **Password**: your-super-secret-password (from .env)
- **Database**: postgres

### API Keys (for local development)

**Anon Key** (public, safe for frontend):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

**Service Role Key** (secret, backend only):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU
```

## Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service definitions |
| `.env.example` | Environment variable template |
| `kong.yml` | Kong API gateway routes |
| `init/01-schema.sql` | Database tables and relationships |
| `init/02-triggers.sql` | Auto-profile creation triggers |
| `init/03-seed-data.sql` | Initial restaurant and menu data |

## Database Schema

The initialization scripts create:

- **User Tables**: `customer_profiles`, `driver_profiles`, `user_types`, `driverdetails`
- **Business Tables**: `restaurant`, `menu`, `orders`, `reservation`
- **System Tables**: `payments`, `notification`, `geospatial`

All user-related tables have foreign keys to `auth.users` with CASCADE delete.

## Automatic Profile Creation

When a user signs up via Supabase Auth:

1. A trigger detects the new user in `auth.users`
2. Based on `user_type` in metadata:
   - Creates `customer_profiles` entry (if customer)
   - Creates `driver_profiles` + `driverdetails` entry (if driver)
3. Creates `user_types` entry for role tracking

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs -f

# Restart with fresh state
docker-compose down -v
docker-compose up -d
```

### Database connection issues
```bash
# Check if database is healthy
docker-compose ps

# Connect directly to PostgreSQL
docker exec -it supabase-db psql -U postgres
```

### Reset database
```bash
# Remove all data and restart
docker-compose down -v
docker-compose up -d
```

## Switching Between Local and Cloud Supabase

### Use Local Supabase

**Backend `.env`:**
```
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Frontend `.env`:**
```
VITE_SUPABASE_URL=http://localhost:8100
VITE_SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Use Cloud Supabase

**Backend `.env`:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-cloud-anon-key
```

**Frontend `.env`:**
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_KEY=your-cloud-anon-key
```

## Stopping Services

```bash
# Stop but keep data
docker-compose down

# Stop and remove all data
docker-compose down -v
```
