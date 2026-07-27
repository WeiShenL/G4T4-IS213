#!/bin/bash

# Wait for Kong to be available
echo "Waiting for Kong API Gateway to be ready..."
while ! curl -s http://kong:8001 > /dev/null; do
    sleep 5
    echo "Still waiting for Kong..."
done

echo "Kong is ready! Setting up services and routes..."

# Clean up any existing services and routes to avoid conflicts
echo "Cleaning up existing configuration..."

# Get all routes and delete them
ROUTES=$(curl -s http://kong:8001/routes | grep -o '"id":"[^"]*"' | sed 's/"id":"//' | sed 's/"//')
for route_id in $ROUTES; do
  echo "Deleting route $route_id"
  curl -s -X DELETE http://kong:8001/routes/$route_id > /dev/null
done

# Get all services and delete them
SERVICES=$(curl -s http://kong:8001/services | grep -o '"id":"[^"]*"' | sed 's/"id":"//' | sed 's/"//')
for service_id in $SERVICES; do
  echo "Deleting service $service_id"
  curl -s -X DELETE http://kong:8001/services/$service_id > /dev/null
done

# Simple Services
echo "Setting up simple services..."

# User Service
echo "Setting up User Service..."
curl -s -X POST http://kong:8001/services \
  --data name=user \
  --data url=http://user-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/user/routes \
  --data name=user-route \
  --data paths=/api/user \
  --data strip_path=false > /dev/null

# Restaurant Service
echo "Setting up Restaurant Service..."
curl -s -X POST http://kong:8001/services \
  --data name=restaurant \
  --data url=http://restaurant-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/restaurant/routes \
  --data name=restaurants-all-route \
  --data paths=/api/restaurants \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/restaurant/routes \
  --data name=restaurant-health \
  --data paths=/api/restaurant/health \
  --data strip_path=false > /dev/null

# Reservation Service
echo "Setting up Reservation Service..."
curl -s -X POST http://kong:8001/services \
  --data name=reservation \
  --data url=http://reservation-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/reservation/routes \
  --data name=reservations-all-route \
  --data paths=/api/reservations \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/reservation/routes \
  --data name=reservation-health-route \
  --data paths=/api/reservation \
  --data strip_path=false > /dev/null

# Menu Service
echo "Setting up Menu Service..."
curl -s -X POST http://kong:8001/services \
  --data name=menu \
  --data url=http://menu-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/menu/routes \
  --data name=menu-all-route \
  --data paths=/api/menu \
  --data strip_path=false > /dev/null


# Order Service
echo "Setting up Order Service..."
curl -s -X POST http://kong:8001/services \
  --data name=order \
  --data url=http://order-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/order/routes \
  --data name=orders-all-route \
  --data paths=/api/orders \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/order/routes \
  --data name=order-health-route \
  --data paths=/api/order \
  --data strip_path=false > /dev/null


# Payment Service
echo "Setting up Payment Service..."
curl -s -X POST http://kong:8001/services \
  --data name=payment \
  --data url=http://payment-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/payment/routes \
  --data name=payment-all-route \
  --data paths=/api/payment \
  --data strip_path=false > /dev/null

# Notification Service
echo "Setting up Notification Service..."
curl -s -X POST http://kong:8001/services \
  --data name=notification \
  --data url=http://notification-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/notification/routes \
  --data name=notification-all-route \
  --data paths=/api/notification \
  --data strip_path=false > /dev/null


# Driver Service
echo "Setting up Driver Service..."
curl -s -X POST http://kong:8001/services \
  --data name=driver \
  --data url=http://driver-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/driver/routes \
  --data name=driver-all-route \
  --data paths=/api/driver \
  --data strip_path=false > /dev/null


# Driver Details Service
echo "Setting up Driver Details Service..."
curl -s -X POST http://kong:8001/services \
  --data name=driver-details \
  --data url=http://driver-details-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/driver-details/routes \
  --data name=driver-details-all-route \
  --data paths=/api/driverdetails \
  --data strip_path=false > /dev/null

# Geo Service
echo "Setting up Geo Service..."
curl -s -X POST http://kong:8001/services \
  --data name=geo \
  --data url=http://geo-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/geo/routes \
  --data name=geo-route \
  --data paths=/api/geo/ \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/geo/routes \
  --data name=geo-nearby-route \
  --data paths=/api/nearby-restaurants \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/geo/routes \
  --data name=geo-delete-route \
  --data paths=/api/delete-geospatial \
  --data strip_path=false > /dev/null

# Waitlist Service
echo "Setting up Waitlist Service..."
curl -s -X POST http://kong:8001/services \
  --data name=waitlist \
  --data url=http://waitlist-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/waitlist/routes \
  --data name=waitlist-all-route \
  --data paths=/api/waitlist \
  --data strip_path=false > /dev/null


# Complex Services
echo "Setting up complex services..."

# Create Booking Service
echo "Setting up Create Booking Service..."
curl -s -X POST http://kong:8001/services \
  --data name=create-booking \
  --data url=http://create-booking-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/create-booking/routes \
  --data name=create-booking-create-route \
  --data paths=/api/create \
  --data strip_path=false > /dev/null


# Accept Reallocation Service
echo "Setting up Accept Reallocation Service..."
curl -s -X POST http://kong:8001/services \
  --data name=accept-reallocation \
  --data url=http://accept-reallocation-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/accept-reallocation/routes \
  --data name=accept-reallocation-route \
  --data paths=/api/accept-reallocation \
  --data strip_path=false > /dev/null


# Cancel Booking Service
echo "Setting up Cancel Booking Service..."
curl -s -X POST http://kong:8001/services \
  --data name=cancel-booking \
  --data url=http://cancel-booking-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/cancel-booking/routes \
  --data name=cancel-booking-route \
  --data paths=/api/cancel \
  --data strip_path=false > /dev/null


# Reallocate Reservation Service
echo "Setting up Reallocate Reservation Service..."
curl -s -X POST http://kong:8001/services \
  --data name=reallocate-reservation \
  --data url=http://reallocate-reservation-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/reallocate-reservation/routes \
  --data name=reallocate-reservation-route \
  --data paths=/api/reallocate \
  --data strip_path=false > /dev/null


# Driver Status Service
echo "Setting up Driver Status Service..."
curl -s -X POST http://kong:8001/services \
  --data name=driver-status \
  --data url=http://driver-status-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/driver-status/routes \
  --data name=driver-status-route \
  --data paths=/api/driver-status \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/driver-status/routes \
  --data name=driver-status-accept-route \
  --data paths=/api/accept-order \
  --data strip_path=false > /dev/null
  
curl -s -X POST http://kong:8001/services/driver-status/routes \
  --data name=driver-status-pick-up-route \
  --data paths=/api/pick-up-order \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/driver-status/routes \
  --data name=driver-status-deliver-route \
  --data paths=/api/deliver-order \
  --data strip_path=false > /dev/null


# DMS Service
echo "Setting up DMS Service..."
curl -s -X POST http://kong:8001/services \
  --data name=dms \
  --data url=http://dms-service:5000 > /dev/null

curl -s -X POST http://kong:8001/services/dms/routes \
  --data name=dms-assign-route \
  --data paths=/api/dms \
  --data strip_path=false > /dev/null

curl -s -X POST http://kong:8001/services/dms/routes \
  --data name=dms-delivery-management \
  --data paths=/api/delivery-management \
  --data strip_path=false > /dev/null


# Verify all services and routes
echo "Verifying Kong configuration..."
SERVICES_COUNT=$(curl -s http://kong:8001/services | grep -o '"id":"[^"]*"' | wc -l)
ROUTES_COUNT=$(curl -s http://kong:8001/routes | grep -o '"id":"[^"]*"' | wc -l)

echo "Successfully configured $SERVICES_COUNT services and $ROUTES_COUNT routes."
echo "Kong setup complete! All services and routes have been registered."
echo "You can access the Kong API Gateway at http://localhost:8000"
echo "The Kong Admin API is available at http://localhost:8001"
echo "The Kong Manager (GUI) is available at http://localhost:8002"

# Test 1 service as a simple health check
TEST_RESPONSE=$(curl -s http://kong:8001/services/restaurant 2>&1)
if [[ $TEST_RESPONSE == *"restaurant"* ]]; then
  echo "✓ Health check passed: Restaurant service is properly configured."
else
  echo "⚠️ Warning: Could not verify restaurant service configuration."
fi

# ============================================
# Global CORS Plugin
# ============================================
echo "Setting up global CORS plugin..."

# Remove any existing global CORS plugins to avoid duplicates
EXISTING_CORS=$(curl -s http://kong:8001/plugins | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"//' | sed 's/"//')
if [ -n "$EXISTING_CORS" ]; then
  # Check if it's a cors plugin before deleting
  for plugin_id in $(curl -s http://kong:8001/plugins | grep -o '"id":"[^"]*"' | sed 's/"id":"//' | sed 's/"//'); do
    PLUGIN_NAME=$(curl -s http://kong:8001/plugins/$plugin_id | grep -o '"name":"[^"]*"' | sed 's/"name":"//' | sed 's/"//')
    if [ "$PLUGIN_NAME" = "cors" ]; then
      echo "Removing existing CORS plugin $plugin_id"
      curl -s -X DELETE http://kong:8001/plugins/$plugin_id > /dev/null
    fi
  done
fi

# Read allowed origins from environment variable (set in docker-compose.yaml)
CORS_ORIGINS="${ALLOWED_ORIGINS:-http://localhost:5173}"
echo "Configuring CORS with origins: $CORS_ORIGINS"

# Install global CORS plugin (applies to ALL routes)
curl -s -X POST http://kong:8001/plugins \
  --data "name=cors" \
  --data "config.origins=$CORS_ORIGINS" \
  --data "config.methods=GET" \
  --data "config.methods=POST" \
  --data "config.methods=PUT" \
  --data "config.methods=PATCH" \
  --data "config.methods=DELETE" \
  --data "config.methods=OPTIONS" \
  --data "config.headers=Content-Type" \
  --data "config.headers=Authorization" \
  --data "config.headers=Accept" \
  --data "config.credentials=true" \
  --data "config.max_age=3600" \
  --data "config.preflight_continue=false" > /dev/null

# Verify CORS plugin was installed
CORS_CHECK=$(curl -s http://kong:8001/plugins | grep -o '"name":"cors"')
if [ -n "$CORS_CHECK" ]; then
  echo "✓ Global CORS plugin installed successfully."
  echo "  - Origins: $CORS_ORIGINS"
  echo "  - Preflight caching: 3600s (1 hour)"
  echo "  - Preflight continue: false (Kong handles OPTIONS directly)"
else
  echo "⚠️ Warning: CORS plugin may not have been installed correctly."
fi

echo ""
echo "Kong setup complete!"