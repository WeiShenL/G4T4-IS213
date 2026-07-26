-- ============================================
-- FeastFinder Database Schema for Local Supabase
-- ============================================
-- This script sets up all tables, relationships, triggers,
-- and seed data for the FeastFinder application
-- ============================================

-- ===========================================
-- Extension Setup
-- ===========================================
-- supabase/postgres image security-restricts pg_read_file, which CREATE EXTENSION
-- calls internally. Wrap so a failure here doesn't abort the whole init script.
-- uuid-ossp is likely pre-installed by the image anyway; gen_random_uuid() is built-in.
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- ===========================================
-- Table: restaurant (no dependencies)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.restaurant (
  restaurant_id SERIAL PRIMARY KEY,
  capacity INTEGER NOT NULL,
  availability BOOLEAN NOT NULL DEFAULT true,
  name VARCHAR(255) NOT NULL,
  address TEXT NOT NULL,
  rating VARCHAR(50) NOT NULL,
  cuisine VARCHAR(255) NOT NULL
);

-- ===========================================
-- Table: customer_profiles (depends on auth.users)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.customer_profiles (
  id UUID NOT NULL PRIMARY KEY,
  customer_name TEXT NOT NULL,
  phone_number VARCHAR(20) NOT NULL,
  street_address TEXT NOT NULL,
  postal_code INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT customer_profiles_id_fkey
    FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- ===========================================
-- Table: driver_profiles (depends on auth.users)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.driver_profiles (
  id UUID NOT NULL PRIMARY KEY,
  driver_name TEXT NOT NULL,
  phone_number VARCHAR(20) NOT NULL,
  street_address TEXT NOT NULL,
  postal_code INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT driver_profiles_id_fkey
    FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- ===========================================
-- Table: user_types (depends on auth.users)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.user_types (
  user_id UUID NOT NULL PRIMARY KEY,
  user_type TEXT NOT NULL,
  CONSTRAINT user_types_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
  CONSTRAINT user_types_user_type_check
    CHECK (user_type IN ('customer', 'driver'))
);

-- ===========================================
-- Table: driverdetails (depends on driver_profiles)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.driverdetails (
  driverdetail_id SERIAL PRIMARY KEY,
  driver_id UUID NOT NULL,
  live_location VARCHAR,
  availability BOOLEAN DEFAULT false,
  total_deliveries INTEGER NOT NULL DEFAULT 0,
  total_earnings NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
  CONSTRAINT driverdetails_driver_id_fkey
    FOREIGN KEY (driver_id) REFERENCES public.driver_profiles(id) ON DELETE CASCADE
);

-- ===========================================
-- Table: menu (depends on restaurant)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.menu (
  menu_id SERIAL PRIMARY KEY,
  restaurant_id INTEGER NOT NULL,
  item_name VARCHAR(255) NOT NULL,
  description TEXT,
  price NUMERIC(10, 2) NOT NULL,
  CONSTRAINT menu_restaurant_id_fkey
    FOREIGN KEY (restaurant_id) REFERENCES public.restaurant(restaurant_id)
);

-- ===========================================
-- Table: orders (depends on auth.users, restaurant)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.orders (
  order_id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  restaurant_id INTEGER NOT NULL,
  item_name VARCHAR(255) NOT NULL,
  quantity INTEGER NOT NULL,
  order_price NUMERIC(10, 2) NOT NULL,
  payment_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  order_type TEXT,
  CONSTRAINT orders_restaurant_id_fkey
    FOREIGN KEY (restaurant_id) REFERENCES public.restaurant(restaurant_id),
  CONSTRAINT orders_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- ===========================================
-- Table: reservation (depends on auth.users, restaurant)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.reservation (
  reservation_id SERIAL PRIMARY KEY,
  restaurant_id INTEGER NOT NULL,
  user_id UUID,
  table_no INTEGER DEFAULT 1,
  status VARCHAR(255) NOT NULL,
  count INTEGER DEFAULT 10,
  price NUMERIC(10, 2),
  time TIMESTAMP,
  order_id SMALLINT,
  payment_id VARCHAR(255),
  CONSTRAINT reservation_restaurant_id_fkey
    FOREIGN KEY (restaurant_id) REFERENCES public.restaurant(restaurant_id),
  CONSTRAINT reservation_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- ===========================================
-- Table: payments (no dependencies)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.payments (
  payment_id SERIAL PRIMARY KEY,
  stripe_payment_id VARCHAR(255) NOT NULL,
  amount NUMERIC(10, 2) NOT NULL,
  status VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- Table: notification (no dependencies)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.notification (
  notification_id BIGSERIAL PRIMARY KEY,
  message VARCHAR,
  status BOOLEAN,
  type VARCHAR,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===========================================
-- Table: waitlist (depends on auth.users, restaurant)
-- Replaces OutSystems dependency for waitlist management
-- ===========================================
CREATE TABLE IF NOT EXISTS public.waitlist (
  waitlist_id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  restaurant_id INTEGER NOT NULL,
  timestamp_added TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status VARCHAR(50) NOT NULL DEFAULT 'waiting',
  CONSTRAINT waitlist_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
  CONSTRAINT waitlist_restaurant_id_fkey
    FOREIGN KEY (restaurant_id) REFERENCES public.restaurant(restaurant_id) ON DELETE CASCADE
);

-- Create indexes for faster waitlist queries
CREATE INDEX IF NOT EXISTS waitlist_restaurant_id_idx ON public.waitlist (restaurant_id);
CREATE INDEX IF NOT EXISTS waitlist_user_id_idx ON public.waitlist (user_id);
CREATE INDEX IF NOT EXISTS waitlist_status_idx ON public.waitlist (status);
CREATE INDEX IF NOT EXISTS waitlist_timestamp_idx ON public.waitlist (timestamp_added);

-- ===========================================
-- Table: geospatial (depends on driver_profiles, orders, restaurant)
-- ===========================================
CREATE TABLE IF NOT EXISTS public.geospatial (
  geo_id SERIAL PRIMARY KEY,
  driver_id UUID,
  restaurant_id INTEGER,
  order_id INTEGER,
  distance TEXT,
  CONSTRAINT geospatial_driver_id_fkey
    FOREIGN KEY (driver_id) REFERENCES public.driver_profiles(id) ON DELETE CASCADE,
  CONSTRAINT geospatial_order_id_fkey
    FOREIGN KEY (order_id) REFERENCES public.orders(order_id),
  CONSTRAINT geospatial_restaurant_id_fkey
    FOREIGN KEY (restaurant_id) REFERENCES public.restaurant(restaurant_id)
);

-- ===========================================
-- Grant Permissions for Supabase Roles
-- ===========================================
-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- Grant all privileges on all tables to service_role
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Grant select/insert/update/delete to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant select to anonymous users (for public data like restaurants, menus)
GRANT SELECT ON public.restaurant TO anon;
GRANT SELECT ON public.menu TO anon;

-- Ensure future tables get proper permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO authenticated;
