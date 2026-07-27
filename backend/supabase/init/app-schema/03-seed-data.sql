-- ============================================
-- FeastFinder Seed Data
-- ============================================
-- Initial restaurants and menu items for testing
-- ============================================

-- ===========================================
-- Restaurant Data
-- ===========================================
INSERT INTO public.restaurant (restaurant_id, capacity, availability, name, address, rating, cuisine)
VALUES
  (1, 50, true, 'Sushi Haven', '10 Orchard Road, Singapore 238838', '4.8', 'Japanese'),
  (2, 50, true, 'Pasta Paradise', '123 Pasta Lane, Singapore 123456', '4.7', 'Italian'),
  (3, 1, true, 'Spice Garden', '45 Little India, Singapore 218025', '4.5', 'Indian'),
  (4, 60, true, 'Dragon Palace', '88 Chinatown Way, Singapore 059102', '4.6', 'Chinese'),
  (5, 35, true, 'Thai Orchid', '22 Boat Quay, Singapore 049822', '4.4', 'Thai'),
  (6, 45, true, 'Burger Barn', '15 Clarke Quay, Singapore 179023', '4.3', 'American'),
  (7, 55, true, 'Seoul Kitchen', '33 Tanjong Pagar, Singapore 088455', '4.7', 'Korean'),
  (8, 30, true, 'Mediterranean Breeze', '77 Marina Bay, Singapore 018956', '4.5', 'Mediterranean')
ON CONFLICT (restaurant_id) DO NOTHING;

-- Synchronize sequence
SELECT setval(pg_get_serial_sequence('public.restaurant', 'restaurant_id'), (SELECT MAX(restaurant_id) FROM public.restaurant));

-- ===========================================
-- Menu Data for Restaurant 1 (Sushi Haven)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (1, 'Omakase Set', 'Chef''s choice 12-piece premium sushi selection', 88.00),
  (1, 'Salmon Lovers Platter', '8 pieces of assorted salmon sushi and sashimi', 45.00),
  (1, 'Chirashi Don', 'Premium sashimi over seasoned rice', 38.00),
  (1, 'Tempura Udon Set', 'Hot udon noodles with crispy tempura', 24.00)
ON CONFLICT DO NOTHING;

-- ===========================================
-- Menu Data for Restaurant 2 (Pasta Paradise)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (2, 'Family Pasta Feast', 'Package includes: 2 pasta mains, 2 sides, 4 drinks and dessert', 59.99),
  (2, 'Date Night Combo', 'Package includes: 2 premium pasta dishes, 2 glasses of wine, and tiramisu to share', 49.99),
  (2, 'Solo Pasta Delight', 'Package includes: 1 pasta main, 1 side salad, 1 drink', 24.99),
  (2, 'Party Platter Special', 'Package includes: 5 pasta mains, 3 sides, garlic bread, and dessert platter', 119.99)
ON CONFLICT DO NOTHING;

-- ===========================================
-- Menu Data for Restaurant 3 (Spice Garden)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (3, 'Butter Chicken Set', 'Creamy tomato curry with naan and rice', 22.00),
  (3, 'Biryani Royale', 'Fragrant basmati rice with tender lamb', 28.00),
  (3, 'Vegetarian Thali', 'Assorted vegetarian dishes with bread and rice', 18.00),
  (3, 'Tandoori Mixed Grill', 'Selection of tandoor-grilled meats', 35.00)
ON CONFLICT DO NOTHING;

-- ===========================================
-- Menu Data for Restaurant 4 (Dragon Palace)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (4, 'Peking Duck Set', 'Whole roasted duck with pancakes and condiments', 68.00),
  (4, 'Dim Sum Platter', 'Assortment of 12 pieces of steamed and fried dim sum', 32.00),
  (4, 'Seafood Hot Pot', 'Fresh seafood in rich broth', 48.00),
  (4, 'Char Siu Rice', 'BBQ pork over steamed rice', 16.00)
ON CONFLICT DO NOTHING;

-- ===========================================
-- Menu Data for Restaurant 5 (Thai Orchid)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (5, 'Tom Yum Goong Set', 'Spicy prawn soup with rice', 22.00),
  (5, 'Pad Thai Classic', 'Stir-fried rice noodles with prawns', 18.00),
  (5, 'Green Curry Chicken', 'Authentic Thai green curry', 20.00),
  (5, 'Mango Sticky Rice', 'Sweet coconut rice with fresh mango', 12.00)
ON CONFLICT DO NOTHING;

-- ===========================================
-- Menu Data for Restaurant 6 (Burger Barn)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (6, 'Classic Cheeseburger', 'Beef patty with cheese, lettuce, tomato', 15.00),
  (6, 'BBQ Bacon Burger', 'Smoky BBQ sauce with crispy bacon', 18.00),
  (6, 'Veggie Burger', 'Plant-based patty with all the fixings', 16.00),
  (6, 'Loaded Fries', 'Fries topped with cheese, bacon, and jalape\u00f1os', 12.00)
ON CONFLICT DO NOTHING;

-- ===========================================
-- Menu Data for Restaurant 7 (Seoul Kitchen)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (7, 'Korean BBQ Set', 'Assorted meats with banchan sides', 45.00),
  (7, 'Bibimbap', 'Mixed rice bowl with vegetables and gochujang', 18.00),
  (7, 'Kimchi Jjigae', 'Spicy kimchi stew with pork', 20.00),
  (7, 'Japchae', 'Sweet potato noodles with vegetables', 16.00)
ON CONFLICT DO NOTHING;

-- ===========================================
-- Menu Data for Restaurant 8 (Mediterranean Breeze)
-- ===========================================
INSERT INTO public.menu (restaurant_id, item_name, description, price)
VALUES
  (8, 'Mezze Platter', 'Hummus, falafel, pita, and dips', 24.00),
  (8, 'Lamb Shawarma Plate', 'Slow-roasted lamb with rice and salad', 26.00),
  (8, 'Grilled Sea Bass', 'Fresh fish with Mediterranean herbs', 32.00),
  (8, 'Greek Salad', 'Fresh vegetables with feta and olives', 14.00)
ON CONFLICT DO NOTHING;
