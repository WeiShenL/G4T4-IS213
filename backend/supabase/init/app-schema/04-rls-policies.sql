-- ============================================
-- FeastFinder Row Level Security (RLS) Policies
-- ============================================
-- These policies control access to data at the row level.
-- Each policy is preceded by a DROP IF EXISTS so this file is re-runnable
-- without error (PG <17 has no CREATE POLICY IF NOT EXISTS).
-- ============================================

-- ===========================================
-- Enable RLS on all tables (idempotent)
-- ===========================================
ALTER TABLE public.customer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.driver_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reservation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.driverdetails ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.restaurant ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.menu ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geospatial ENABLE ROW LEVEL SECURITY;

-- ===========================================
-- Customer Profiles Policies
-- ===========================================
DROP POLICY IF EXISTS "Users can view own customer profile" ON public.customer_profiles;
CREATE POLICY "Users can view own customer profile" ON public.customer_profiles
  FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own customer profile" ON public.customer_profiles;
CREATE POLICY "Users can update own customer profile" ON public.customer_profiles
  FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own customer profile" ON public.customer_profiles;
CREATE POLICY "Users can insert own customer profile" ON public.customer_profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Service role can manage customer profiles" ON public.customer_profiles;
CREATE POLICY "Service role can manage customer profiles" ON public.customer_profiles
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Driver Profiles Policies
-- ===========================================
DROP POLICY IF EXISTS "Users can view own driver profile" ON public.driver_profiles;
CREATE POLICY "Users can view own driver profile" ON public.driver_profiles
  FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own driver profile" ON public.driver_profiles;
CREATE POLICY "Users can update own driver profile" ON public.driver_profiles
  FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own driver profile" ON public.driver_profiles;
CREATE POLICY "Users can insert own driver profile" ON public.driver_profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Service role can manage driver profiles" ON public.driver_profiles;
CREATE POLICY "Service role can manage driver profiles" ON public.driver_profiles
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- User Types Policies
-- ===========================================
DROP POLICY IF EXISTS "Users can view own user type" ON public.user_types;
CREATE POLICY "Users can view own user type" ON public.user_types
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own user type" ON public.user_types;
CREATE POLICY "Users can insert own user type" ON public.user_types
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage user types" ON public.user_types;
CREATE POLICY "Service role can manage user types" ON public.user_types
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Orders Policies
-- ===========================================
DROP POLICY IF EXISTS "Users can view own orders" ON public.orders;
CREATE POLICY "Users can view own orders" ON public.orders
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Drivers can view delivery orders" ON public.orders;
CREATE POLICY "Drivers can view delivery orders" ON public.orders
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.user_types
      WHERE user_id = auth.uid() AND user_type = 'driver'
    ) AND order_type = 'delivery'
  );

DROP POLICY IF EXISTS "Users can insert own orders" ON public.orders;
CREATE POLICY "Users can insert own orders" ON public.orders
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage orders" ON public.orders;
CREATE POLICY "Service role can manage orders" ON public.orders
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Reservations Policies
-- ===========================================
DROP POLICY IF EXISTS "Users can view own reservations" ON public.reservation;
CREATE POLICY "Users can view own reservations" ON public.reservation
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own reservations" ON public.reservation;
CREATE POLICY "Users can insert own reservations" ON public.reservation
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage reservations" ON public.reservation;
CREATE POLICY "Service role can manage reservations" ON public.reservation
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Waitlist Policies
-- ===========================================
DROP POLICY IF EXISTS "Users can view own waitlist entries" ON public.waitlist;
CREATE POLICY "Users can view own waitlist entries" ON public.waitlist
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own waitlist entries" ON public.waitlist;
CREATE POLICY "Users can insert own waitlist entries" ON public.waitlist
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage waitlist" ON public.waitlist;
CREATE POLICY "Service role can manage waitlist" ON public.waitlist
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Driver Details Policies
-- ===========================================
DROP POLICY IF EXISTS "Drivers can view own details" ON public.driverdetails;
CREATE POLICY "Drivers can view own details" ON public.driverdetails
  FOR SELECT USING (auth.uid() = driver_id);

DROP POLICY IF EXISTS "Drivers can update own details" ON public.driverdetails;
CREATE POLICY "Drivers can update own details" ON public.driverdetails
  FOR UPDATE USING (auth.uid() = driver_id);

DROP POLICY IF EXISTS "Service role can manage driver details" ON public.driverdetails;
CREATE POLICY "Service role can manage driver details" ON public.driverdetails
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Restaurant Policies (public-readable catalog)
-- ===========================================
DROP POLICY IF EXISTS "Anyone can view restaurants" ON public.restaurant;
CREATE POLICY "Anyone can view restaurants" ON public.restaurant
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "Service role can manage restaurants" ON public.restaurant;
CREATE POLICY "Service role can manage restaurants" ON public.restaurant
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Menu Policies (public-readable catalog)
-- ===========================================
DROP POLICY IF EXISTS "Anyone can view menu" ON public.menu;
CREATE POLICY "Anyone can view menu" ON public.menu
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "Service role can manage menu" ON public.menu;
CREATE POLICY "Service role can manage menu" ON public.menu
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Payments Policies (service role only)
-- ===========================================
DROP POLICY IF EXISTS "Service role can manage payments" ON public.payments;
CREATE POLICY "Service role can manage payments" ON public.payments
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Notifications Policies (service role only)
-- ===========================================
DROP POLICY IF EXISTS "Service role can manage notifications" ON public.notification;
CREATE POLICY "Service role can manage notifications" ON public.notification
  FOR ALL USING (auth.role() = 'service_role');

-- ===========================================
-- Geospatial Policies
-- ===========================================
DROP POLICY IF EXISTS "Drivers can view geospatial data" ON public.geospatial;
CREATE POLICY "Drivers can view geospatial data" ON public.geospatial
  FOR SELECT USING (auth.uid() = driver_id);

DROP POLICY IF EXISTS "Service role can manage geospatial" ON public.geospatial;
CREATE POLICY "Service role can manage geospatial" ON public.geospatial
  FOR ALL USING (auth.role() = 'service_role');
