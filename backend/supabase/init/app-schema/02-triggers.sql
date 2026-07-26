-- ============================================
-- FeastFinder Database Triggers
-- ============================================
-- These triggers automatically create user profiles
-- and user_types entries when new users sign up
-- ============================================

-- ===========================================
-- Function: Handle New User Signup
-- Creates profile and user_type based on metadata
-- ===========================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  user_type_value TEXT;
  user_name TEXT;
  user_phone TEXT;
  user_address TEXT;
  user_postal INTEGER;
BEGIN
  -- Extract user type from metadata
  user_type_value := NEW.raw_user_meta_data->>'user_type';

  -- If no user_type provided, default to 'customer'
  IF user_type_value IS NULL OR user_type_value = '' THEN
    user_type_value := 'customer';
  END IF;

  -- Extract common fields from metadata
  user_name := COALESCE(NEW.raw_user_meta_data->>'name', 'Unknown');
  user_phone := COALESCE(NEW.raw_user_meta_data->>'phone', '');
  user_address := COALESCE(NEW.raw_user_meta_data->>'address', '');
  user_postal := COALESCE((NEW.raw_user_meta_data->>'postal_code')::INTEGER, 0);

  -- Insert into user_types table
  INSERT INTO public.user_types (user_id, user_type)
  VALUES (NEW.id, user_type_value)
  ON CONFLICT (user_id) DO NOTHING;

  -- Create appropriate profile based on user type
  IF user_type_value = 'customer' THEN
    INSERT INTO public.customer_profiles (id, customer_name, phone_number, street_address, postal_code)
    VALUES (NEW.id, user_name, user_phone, user_address, user_postal)
    ON CONFLICT (id) DO NOTHING;
  ELSIF user_type_value = 'driver' THEN
    INSERT INTO public.driver_profiles (id, driver_name, phone_number, street_address, postal_code)
    VALUES (NEW.id, user_name, user_phone, user_address, user_postal)
    ON CONFLICT (id) DO NOTHING;

    -- Also create a driver details entry
    INSERT INTO public.driverdetails (driver_id, availability, total_deliveries, total_earnings)
    VALUES (NEW.id, false, 0, 0.00)
    ON CONFLICT DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================================
-- Trigger: On Auth User Created
-- ===========================================
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ===========================================
-- Function: Update timestamp on profile changes
-- ===========================================
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- Trigger: Auto-update timestamps
-- ===========================================
DROP TRIGGER IF EXISTS update_customer_profiles_updated_at ON public.customer_profiles;
CREATE TRIGGER update_customer_profiles_updated_at
  BEFORE UPDATE ON public.customer_profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_driver_profiles_updated_at ON public.driver_profiles;
CREATE TRIGGER update_driver_profiles_updated_at
  BEFORE UPDATE ON public.driver_profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- ===========================================
-- Realtime Publication for Live Updates
-- Enables Supabase Realtime subscriptions
-- ===========================================
-- Add the tables the dashboards subscribe to for live updates: orders and
-- driverdetails for the driver dashboard, reservation for the customer dashboard's
-- pending table offer.
-- Idempotent: skip any table already a member of the publication.
DO $$
DECLARE
  t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['orders', 'driverdetails', 'reservation'] LOOP
    IF NOT EXISTS (
      SELECT 1 FROM pg_publication_tables
      WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = t
    ) THEN
      EXECUTE format('ALTER PUBLICATION supabase_realtime ADD TABLE public.%I', t);
    END IF;
  END LOOP;
END $$;
