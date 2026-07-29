#!/bin/bash
# Creates all Supabase-required PostgreSQL roles and the realtime publication.
# Must run before the schema/trigger SQL files (hence the 00- prefix).
# Mounting ./init to /docker-entrypoint-initdb.d replaces the supabase/postgres
# image's own built-in role-creation scripts, so we recreate them here.
set -e

PASS="${POSTGRES_PASSWORD:-your-super-secret-password}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL

DO \$\$ BEGIN CREATE ROLE supabase_admin; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
-- SUPERUSER matches the official Supabase setup. postgres-meta (Studio backend)
-- connects as this role; without SUPERUSER it can't read tables it doesn't own.
ALTER ROLE supabase_admin WITH SUPERUSER LOGIN CREATEROLE CREATEDB REPLICATION BYPASSRLS PASSWORD '$PASS';

DO \$\$ BEGIN CREATE ROLE supabase_auth_admin; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE supabase_auth_admin WITH NOINHERIT CREATEROLE LOGIN NOREPLICATION PASSWORD '$PASS';

DO \$\$ BEGIN CREATE ROLE supabase_storage_admin; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE supabase_storage_admin WITH NOINHERIT CREATEROLE LOGIN NOREPLICATION PASSWORD '$PASS';

DO \$\$ BEGIN CREATE ROLE supabase_realtime_admin; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE supabase_realtime_admin WITH NOINHERIT CREATEROLE LOGIN NOREPLICATION PASSWORD '$PASS';

DO \$\$ BEGIN CREATE ROLE supabase_replication_admin; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE supabase_replication_admin WITH LOGIN REPLICATION PASSWORD '$PASS';

DO \$\$ BEGIN CREATE ROLE anon; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE anon NOLOGIN NOINHERIT;

DO \$\$ BEGIN CREATE ROLE authenticated; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE authenticated NOLOGIN NOINHERIT;

DO \$\$ BEGIN CREATE ROLE service_role; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;

DO \$\$ BEGIN CREATE ROLE authenticator; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
ALTER ROLE authenticator WITH NOINHERIT LOGIN PASSWORD '$PASS';

GRANT anon TO authenticator;
GRANT authenticated TO authenticator;
GRANT service_role TO authenticator;
GRANT supabase_admin TO postgres;

GRANT ALL ON SCHEMA public TO supabase_admin, supabase_auth_admin, supabase_storage_admin, supabase_realtime_admin;
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- auth schema: GoTrue's first migration tries to CREATE TABLE auth.users
-- but does not CREATE SCHEMA itself — supabase/postgres image normally does this.
CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION supabase_auth_admin;
CREATE TABLE IF NOT EXISTS auth.users (
  id uuid NOT NULL PRIMARY KEY,
  raw_user_meta_data jsonb
);
GRANT ALL ON SCHEMA auth TO supabase_auth_admin;
GRANT ALL ON ALL TABLES IN SCHEMA auth TO supabase_auth_admin;
GRANT USAGE ON SCHEMA auth TO authenticated, anon, service_role;

-- GoTrue migrations create types without schema prefix (e.g. "factor_type" not "auth.factor_type").
-- search_path must be "auth" so unqualified names land in the auth schema, not public.
ALTER ROLE supabase_auth_admin SET search_path = auth;

-- _realtime schema: supabase-realtime sets search_path to _realtime on connect,
-- then tries to create its schema_migrations table — fails if the schema doesn't exist.
CREATE SCHEMA IF NOT EXISTS _realtime AUTHORIZATION supabase_admin;
GRANT ALL ON SCHEMA _realtime TO supabase_admin, supabase_realtime_admin;

-- realtime schema (distinct from _realtime): holds subscription and list_changes(),
-- which postgres_changes needs. /app/bin/migrate only builds _realtime (the tenant
-- control plane); the tenant migrations that create realtime.subscription run on first
-- tenant connect and silently fail if the schema is absent, so every postgres_changes
-- subscription errors with 'relation "realtime.subscription" does not exist' while the
-- client still reports SUBSCRIBED. Creating the schema is enough — realtime populates it.
CREATE SCHEMA IF NOT EXISTS realtime AUTHORIZATION supabase_admin;
GRANT ALL ON SCHEMA realtime TO supabase_admin, supabase_realtime_admin;

-- Needed by 02-triggers.sql and the realtime service
DO \$\$ BEGIN
  CREATE PUBLICATION supabase_realtime;
EXCEPTION WHEN duplicate_object THEN NULL;
END \$\$;

EOSQL
