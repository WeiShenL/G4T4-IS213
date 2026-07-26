// DriverDashboard.vue
<template>
  <div>
    <!-- Dashboard Header -->
    <div class="dashboard-header">
      <div class="container">
        <div class="d-flex justify-content-between align-items-center">
          <router-link to="/driver-dashboard" class="dashboard-logo">
            <span>FeastFinder</span>
          </router-link>
          <div class="dashboard-user d-flex align-items-center">
            <div class="dropdown">
              <button class="btn dropdown-toggle" type="button" id="userDropdown" @click="toggleDropdown">
                <i class="fas fa-user-circle"></i>
                <span v-if="user">{{ user.driverName }}</span>
                <span v-else>Loading...</span>
              </button>
              <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
                <li><router-link class="dropdown-item" to="/driver-dashboard"><i class="fas fa-user-cog"></i>My Dashboard</router-link></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item" href="#" @click.prevent="logout"><i class="fas fa-sign-out-alt"></i> Logout</a></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Dashboard Content -->
    <div class="dashboard-container">
      <div class="container">
        <!-- Welcome Message -->
        <div class="row mb-4">
          <div class="col-12">
            <div class="welcome-card">
              <h2>Welcome, <span v-if="user">{{ user.driverName }}</span><span v-else>Driver</span>!</h2>
              <p>Manage your delivery requests and view route navigation</p>

              <!-- Resend Email Notification Banner -->
              <div class="alert alert-info border-0 shadow-sm mt-3 bg-light text-dark text-start">
                <div class="d-flex align-items-center mb-1">
                  <i class="fas fa-paper-plane text-primary me-2 fs-5"></i>
                  <strong>Automated Customer Email Notifications Active!</strong>
                </div>
                <small class="text-muted d-block">
                  When you accept, pick up, or deliver an order, customer status emails are automatically dispatched via Resend API. 
                  <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to the developer's testing inbox).</em>
                </small>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Loading State -->
        <div v-if="isLoading" class="loading-container">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p>Loading your data...</p>
        </div>
        
        <!-- Error Message -->
        <div v-if="errorMessage" class="alert alert-danger" role="alert">
          {{ errorMessage }}
        </div>
        
        <!-- Content shown only when data is loaded -->
        <div v-if="!isLoading && !errorMessage">
          <!-- Driver Stats -->
          <div class="row mb-4">
            <div class="col-md-4 col-sm-6 mb-3" v-for="(stat, index) in driverStats" :key="index">
              <div class="stat-card">
                <div class="stat-icon">
                  <i :class="stat.icon"></i>
                </div>
                <div class="stat-content">
                  <h4>{{ stat.title }}</h4>
                  <p class="stat-value">{{ stat.value }}</p>
                </div>
              </div>
            </div>
          </div>
          
          
          <!-- New Delivery Requests -->
          <div class="row mb-4">
            <div class="col-12 d-flex justify-content-between align-items-center">
              <h3 class="section-heading">New Delivery Requests</h3>
              <button 
                class="btn btn-primary" 
                @click="fetchDeliveryData"
                :disabled="isFetching"
              >
                <span v-if="!isFetching">Check for Deliveries</span>
                <span v-else class="spinner-border spinner-border-sm" role="status"></span>
              </button>
            </div>
            <!-- Empty state shown when no delivery data or no restaurants with orders -->
            <div v-if="!deliveryData || !deliveryData.data || !deliveryData.data.restaurants || deliveryData.data.restaurants.length === 0" class="col-12">
              <div class="empty-state">
                <i class="fas fa-route"></i>
                <p>No new delivery requests at the moment.</p>
                <small>New requests will appear here when available.</small>
              </div>
            </div>
            <!-- Delivery requests list -->
            <div v-else class="col-12 mt-3">
              <div class="delivery-requests-container">
                <div v-for="restaurant in deliveryData.data.restaurants" :key="restaurant.id" class="restaurant-section mb-4">
                  <h4>{{ restaurant.name }}</h4>
                  <p class="restaurant-address"><i class="fas fa-map-marker-alt"></i> {{ restaurant.location }}</p>
                  <div class="order-cards">
                    <div v-for="order in restaurant.orders" :key="order.order_id" class="order-card">
                      <div class="order-details">
                        <h5>Order #{{ order.order_id }}</h5>
                        <p><strong>Item:</strong> {{ order.item_name }}</p>
                        <p><strong>Customer:</strong> {{ order.customer.name }}</p>
                        <p><strong>Delivery to:</strong> {{ order.customer.location }}</p>
                      </div>
                      <button class="btn btn-primary" @click="focusOnRestaurant(order.order_id)">
                        Show on Map
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Map Section -->
          <div class="row mb-4">
            <div class="col-12">
              <h3 class="section-heading">Active Deliveries Map</h3>
              <div class="map-container" ref="mapContainer"></div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { supabaseClient, signOut } from '@/services/supabase';
import { loadGoogleMapsApi } from '@/services/googleMapsLoader';

const API_GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL || 'http://localhost:8000';
const DELIVERY_MANAGEMENT_PATH = '/api/delivery-management';
const DRIVER_DETAILS_PATH = '/api/driverdetails';

export default {
  name: 'DriverDashboard',
  setup() {
    const router = useRouter();
    const user = ref(null);
    const isLoading = ref(true);
    const errorMessage = ref('');
    const deliveryData = ref(null);
    const refreshNeeded = ref(true); // Flag to track if refresh is needed
    const orderSubscription = ref(null); // Supabase realtime subscription

     // Map variables
    const isFetching   = ref(false);
    const map          = ref(null);
    const infoWindow   = ref(null);
    const mapContainer = ref(null);
    const markers = ref([]);

    
    
    const driverStats = [
      {
        icon: 'fas fa-truck',
        title: 'Today\'s Deliveries',
        value: '0'
      },
      {
        icon: 'fas fa-dollar-sign',
        title: 'Today\'s Earnings',
        value: '$0.00'
      },

    ];
      // is this location hard coded here?
    const initMap = () => {
      if (!map.value && mapContainer.value) {
        try {
          map.value = new google.maps.Map(mapContainer.value, {
            center: { lat: 1.3521, lng: 103.8198 },
            zoom: 12
          });
          infoWindow.value = new google.maps.InfoWindow();
          console.log('Map initialized successfully');
        } catch (error) {
          console.error('Error initializing map:', error);
        }
      } 
    };
    window.initMap = initMap;

    // i split the logic to get driver and restaurant locations 
    // separately so that if no restaurants driver still can see his location on map.
    const fetchDeliveryData = async () => {
      isFetching.value = true;
      try {
        const driverId = user.value?.id;
        if (!driverId) {
          throw new Error("Driver ID not available.");
        }

        // 1. Update driver's live location first using Geolocation API to db
        await updateDriverLocation();
        console.log('📍 Updated location via device Geolocation API');

        // 2. Now fetch the delivery management data
        const deliveryUrl = `${API_GATEWAY_URL}${DELIVERY_MANAGEMENT_PATH}?driver_id=${driverId}`;
        console.log('👉 Fetching delivery data:', deliveryUrl);
        
        const response = await fetch(deliveryUrl);
        console.log('👉 Status:', response.status, 'OK?', response.ok);
        
        // If it's not a 2xx, throw so you hit your catch:
        if (!response.ok) {
          const text = await response.text();
          console.error('🚨 Non‑2xx response body:', text);
          
          // means no order found.
          if (response.status === 404) {
            // Set empty data structure instead of error
            deliveryData.value = {
              code: 200,
              data: {
                driver: user.value,
                restaurants: []
              }
            };
            // Show driver location on map
            showDriverLocationOnMap();
            isFetching.value = false;
            return;
          }
          
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('👉 JSON payload:', data);

        // Store the response data for reuse
        deliveryData.value = data;
        
        // Update map with all markers (driver and restaurants)
        updateMapMarkers(data);
        
      } catch (error) {
        console.error('Error fetching delivery data:', error);
        
        // this error happens when there is no order. Handle error gracefully ba.
        if (error.message && error.message.includes("HTTP 500")) {
          console.log("Setting empty deliveries structure instead of showing error");
          // no orders found.
          deliveryData.value = {
            code: 200,
            data: {
              driver: user.value,
              restaurants: []
            }
          };
          // Clear any existing error message
          errorMessage.value = '';
          
          // Show driver location on map
          showDriverLocationOnMap();
        } else {
          // For other errors, show error message
          errorMessage.value = 'Failed to fetch delivery data';
        }
      } finally {
        isFetching.value = false;
      }
    };

    // Function to show driver's current location on the map
    const showDriverLocationOnMap = () => {
      // Check if Google Maps has loaded and map has been initialized
      if (typeof google === 'undefined' || !map.value) {
        console.log('Google Maps not yet loaded or map not initialized. Skipping map updates.');
        return;
      }
      
      // Clear existing markers (check)
      markers.value.forEach(marker => marker.setMap(null));
      markers.value = [];
      
      // Get current position using device GPS/location services
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          console.log(`Using current location for map: ${latitude}, ${longitude}`);
          
          // Set driver marker
          const driverMarker = new google.maps.Marker({
            position: { lat: latitude, lng: longitude },
            map: map.value,
            icon: 'https://maps.google.com/mapfiles/ms/icons/green-dot.png'
          });
          markers.value.push(driverMarker);
          
          // Center the map on driver's location
          map.value.setCenter({ lat: latitude, lng: longitude });
          map.value.setZoom(14);
        },
        (error) => {
          console.error('Error getting current position for map:', error);
          // Fallback to Singapore center if geolocation fails
          map.value.setCenter({ lat: 1.3521, lng: 103.8198 });
          map.value.setZoom(12);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      );
    };
    
    // Function to update map with all markers (driver and restaurants)
    const updateMapMarkers = (data) => {
      // Check if Google Maps has loaded and map has been initialized
      if (typeof google === 'undefined' || !map.value) {
        console.log('Google Maps not yet loaded or map not initialized. Skipping map updates.');
        return;
      }
      
      // Clear existing markers
      markers.value.forEach(marker => marker.setMap(null));
      markers.value = [];
      
      // Set driver marker if valid lat,lng coordinates exist
      if (data.data?.driver?.location && data.data.driver.location.includes(',')) {
        const driverCoords = data.data.driver.location.split(',').map(Number);
        if (!isNaN(driverCoords[0]) && !isNaN(driverCoords[1])) {
          const driverMarker = new google.maps.Marker({
            position: { lat: driverCoords[0], lng: driverCoords[1] },
            map: map.value,
            icon: 'https://maps.google.com/mapfiles/ms/icons/green-dot.png'
          });
          markers.value.push(driverMarker);
        }
      }
      
      // Set restaurant markers
      (data.data?.restaurants || []).forEach(restaurant => {
        if (!restaurant.coordinates || !restaurant.coordinates.includes(',')) return;
        const coords = restaurant.coordinates.split(',').map(Number);
        if (isNaN(coords[0]) || isNaN(coords[1])) return;

        const marker = new google.maps.Marker({
          position: { lat: coords[0], lng: coords[1] },
          map: map.value,
          title: restaurant.name
        });
        
        // Create info window content with select buttons
        const content = document.createElement('div');
        content.className = 'info-window';
        
        const title = document.createElement('h4');
        title.textContent = restaurant.name;
        content.appendChild(title);
        
        const address = document.createElement('p');
        address.textContent = restaurant.location;
        content.appendChild(address);
        
        const ordersList = document.createElement('ul');
        restaurant.orders.forEach(order => {
          const item = document.createElement('li');
          
          const orderInfo = document.createElement('div');
          
          const line1 = document.createElement('span');
          line1.textContent = `${order.item_name} (Order #${order.order_id})`;
          orderInfo.appendChild(line1);
          
          orderInfo.appendChild(document.createElement('br'));
          
          const line2 = document.createElement('span');
          line2.textContent = `To: ${order.customer.name} (${order.customer.location})`;
          orderInfo.appendChild(line2);

          item.appendChild(orderInfo);
          
          const selectBtn = document.createElement('button');
          selectBtn.className = 'btn btn-sm btn-primary mt-2';
          selectBtn.textContent = 'Select';
          selectBtn.onclick = () => selectOrder(order.order_id); // Just pass order ID
          item.appendChild(selectBtn);
          
          ordersList.appendChild(item);
        });
        content.appendChild(ordersList);
        
        marker.addListener('click', () => {
          infoWindow.value.setContent(content);
          infoWindow.value.open(map.value, marker);
        });
        
        markers.value.push(marker);
      });
      
      // Adjust map bounds if there are valid markers
      const validMarkers = markers.value.filter(marker => {
        const pos = marker && marker.getPosition();
        return pos && typeof pos.lat === 'function' && !isNaN(pos.lat()) && !isNaN(pos.lng());
      });

      if (validMarkers.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        validMarkers.forEach(marker => bounds.extend(marker.getPosition()));
        map.value.fitBounds(bounds);
      }
    };

    // Watch for route changes to refresh data when returning to this page
    watch(() => router.currentRoute.value.fullPath, (newPath) => {
      console.log('Route changed, current path:', newPath);
      if (newPath === '/driver-dashboard' && refreshNeeded.value && user.value?.id) {
        console.log('Back on dashboard, refreshing data...');
        fetchDriverStats();
        refreshNeeded.value = false;
        // Reset after a short delay to allow for future refreshes
        setTimeout(() => {
          refreshNeeded.value = true;
        }, 1000);
      }
    });
    
    // Also set refreshNeeded to true when leaving to another route
    const selectOrder = (orderId) => {
      console.log(`Order ${orderId} selected`);
      
      // Find the order across all restaurants
      let selectedOrder = null;
      let selectedRestaurant = null;
      
      for (const restaurant of deliveryData.value?.data.restaurants || []) {
        const order = restaurant.orders.find(order => order.order_id === orderId);
        if (order) {
          selectedOrder = order;
          selectedRestaurant = restaurant;
          break;
        }
      }
      
      if (!selectedOrder || !selectedRestaurant) {
        console.error('Could not find selected order');
        return;
      }
      
      // Store selected data in localStorage before navigating
      const routingData = {
        driver: deliveryData.value.data.driver,
        restaurant: selectedRestaurant,
        order: selectedOrder
      };
      
      localStorage.setItem('routingData', JSON.stringify(routingData));
      
      // Set refresh flag before navigation
      refreshNeeded.value = true;
      
      // Navigate to routing page with just the order ID
      router.push({
        path: '/routing',
        query: { order_id: orderId }
      });
    };

    // Function to focus on a restaurant and order on the map
    const focusOnRestaurant = (orderId) => {
      console.log(`Focusing on order ${orderId} on map`);
      
      // Find the restaurant for this order
      let targetRestaurant = null;
      
      for (const restaurant of deliveryData.value?.data.restaurants || []) {
        if (restaurant.orders.some(order => order.order_id === orderId)) {
          targetRestaurant = restaurant;
          break;
        }
      }
      
      if (!targetRestaurant) {
        console.error('Could not find restaurant for order');
        return;
      }
      
      // Find the corresponding marker
      const coords = targetRestaurant.coordinates.split(',').map(Number);
      
      // Find the marker by position
      const targetMarker = markers.value.find(marker => {
        const position = marker.getPosition();
        return position && 
               Math.abs(position.lat() - coords[0]) < 0.0001 && 
               Math.abs(position.lng() - coords[1]) < 0.0001;
      });
      
      if (!targetMarker) {
        console.error('Could not find marker for restaurant');
        return;
      }
      
      // Scroll to the map container element
      if (mapContainer.value) {
        mapContainer.value.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      
      // Zoom in on the marker
      map.value.setZoom(16);
      map.value.panTo(targetMarker.getPosition());
      
      // Click the marker to open info window
      google.maps.event.trigger(targetMarker, 'click');
    };

    // Fetch driver stats from the driver_status microservice
    const fetchDriverStats = async () => {
      try {
        const driverId = user.value?.id;
        if (!driverId) {
          console.error('Cannot fetch driver stats: No driver ID available');
          return;
        }
        
        console.log('Fetching driver stats from driverdetails msc');
        const response = await fetch(`${API_GATEWAY_URL}${DRIVER_DETAILS_PATH}/${driverId}`);
        
        if (!response.ok) {
          console.error('Failed to fetch driver stats:', response.status);
          return;
        }
        
        const data = await response.json();
        console.log('Driver stats fetched:', data);
        
        if (data.code === 200 && data.data) {
          // Update the driver stats with the fetched values
          driverStats[0].value = data.data.total_deliveries.toString();
          driverStats[1].value = `$${data.data.total_earnings.toFixed(2)}`;
          console.log('Driver stats updated successfully');
        }
      } catch (error) {
        console.error('Error fetching driver stats:', error);
      }
    };

    // Function to update driver location and refresh map marker
    const updateDriverLocation = async () => {
      try {
        const driverId = user.value?.id;
        if (!driverId) {
          console.error("No driver ID available");
          return;
        }

        // Use browser's Geolocation API 
        if (!navigator.geolocation) {
          throw new Error("Geolocation is not supported by this browser");
        }

        // Get current position using device GPS/location services
        navigator.geolocation.getCurrentPosition(
          async (position) => {
            const { latitude, longitude } = position.coords;
            console.log(`Precise location obtained: ${latitude}, ${longitude}`);

            // Update driver location in driverdetail service
            const response = await fetch(`${API_GATEWAY_URL}${DRIVER_DETAILS_PATH}/${driverId}/location`, {
              method: "PATCH",
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                location: `${latitude},${longitude}`,
                accuracy: position.coords.accuracy
              })
            });

            if (!response.ok) {
              const errorData = await response.text();
              throw new Error(`Location update failed: ${errorData}`);
            }

            const data = await response.json();
            console.log("Driver location successfully updated:", data);
            
            // Update driver marker on map if map is initialized
            if (map.value && typeof google !== 'undefined') {
              // Find the driver marker (it's the one with the green icon)
              const driverMarker = markers.value.find(marker => 
                marker.getIcon() === 'https://maps.google.com/mapfiles/ms/icons/green-dot.png'
              );
              
              // If driver marker exists, update its position
              if (driverMarker) {
                const newPosition = new google.maps.LatLng(latitude, longitude);
                
                // Animate the marker movement
                animateMarkerTo(driverMarker, newPosition);
                console.log("Driver marker position updated on map");
              } else {
                // If no driver marker exists, create a new one
                const newDriverMarker = new google.maps.Marker({
                  position: { lat: latitude, lng: longitude },
                  map: map.value,
                  icon: 'https://maps.google.com/mapfiles/ms/icons/green-dot.png',
                  animation: google.maps.Animation.DROP
                });
                markers.value.push(newDriverMarker);
                console.log("New driver marker created on map");
              }
            }
          },
          (error) => {
            let geoErrMsg;
            switch(error.code) {
              case error.PERMISSION_DENIED:
                geoErrMsg = "User denied the request for geolocation";
                break;
              case error.POSITION_UNAVAILABLE:
                geoErrMsg = "Location information is unavailable";
                break;
              case error.TIMEOUT:
                geoErrMsg = "The request to get user location timed out";
                break;
              default:
                geoErrMsg = "An unknown error occurred";
                break;
            }
            console.warn(`Geolocation notice: ${geoErrMsg}`);
          },
          {
            enableHighAccuracy: true, // Request high accuracy GPS data
            timeout: 10000,           // Wait up to 10 seconds
            maximumAge: 0             // Don't use cached position
          }
        );
      } catch (err) {
        console.error("Error updating driver location:", err);
        errorMessage.value = `Failed to update location: ${err.message}`;
      }
    };
    
    // Function to animate marker movement between positions
    const animateMarkerTo = (marker, newPosition) => {
      const startPosition = marker.getPosition();
      const startLat = startPosition.lat();
      const startLng = startPosition.lng();
      const endLat = newPosition.lat();
      const endLng = newPosition.lng();
      
      // Animation duration in ms
      const duration = 1000;
      const fps = 60;
      const frames = duration / (1000 / fps);
      let frame = 0;
      
      const animateStep = () => {
        if (frame >= frames) {
          // Animation complete
          marker.setPosition(newPosition);
          return;
        }
        
        frame++;
        const progress = frame / frames;
        
        // Use easeInOut function for smoother motion
        const easeProgress = progress < 0.5 
          ? 2 * progress * progress 
          : -1 + (4 - 2 * progress) * progress;
          
        const lat = startLat + (endLat - startLat) * easeProgress;
        const lng = startLng + (endLng - startLng) * easeProgress;
        
        marker.setPosition(new google.maps.LatLng(lat, lng));
        
        // Request next animation frame
        requestAnimationFrame(animateStep);
      };
      
      // Start animation
      animateStep();
    };

    // Show a browser notification for a newly available delivery order
    const notifyNewDeliveryOrder = (order) => {
      if (!('Notification' in window) || Notification.permission !== 'granted') {
        return;
      }

      new Notification('New Delivery Order!', {
        body: `Order #${order.order_id} is available for pickup`,
        icon: '/favicon.ico'
      });
    };

    // Setup Supabase Realtime subscription for new delivery orders
    const setupRealtimeSubscription = () => {
      console.log('🔔 Setting up Supabase Realtime subscription for orders...');

      // Subscribe to changes on orders and driverdetails tables
      orderSubscription.value = supabaseClient
        .channel('delivery-orders')
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'orders'
          },
          (payload) => {
            console.log('⚡ Order event received via Realtime:', payload);

            // Notify the driver when a brand new delivery order comes in
            if (payload.eventType === 'INSERT' && payload.new?.order_type === 'delivery') {
              notifyNewDeliveryOrder(payload.new);
            }

            if (user.value?.id && !isFetching.value) {
              fetchDeliveryData();
            }
          }
        )
        .subscribe((status) => {
          console.log('🔔 Realtime subscription status:', status);
        });
    };

    // Cleanup realtime subscription
    const cleanupRealtimeSubscription = () => {
      if (orderSubscription.value) {
        console.log('🔕 Cleaning up Supabase Realtime subscription...');
        supabaseClient.removeChannel(orderSubscription.value);
        orderSubscription.value = null;
      }
    };

    // Request notification permission
    const requestNotificationPermission = async () => {
      if ('Notification' in window) {
        const permission = await Notification.requestPermission();
        console.log('Notification permission:', permission);
      }
    };

    // Load user data when component mounts
    onMounted(async () => {
      try {
        // First check if user is logged in
        const { data: sessionData, error: sessionError } = await supabaseClient.auth.getSession();
        
        if (sessionError) {
          console.error('Session error:', sessionError);
          throw sessionError;
        }
        
        if (!sessionData.session) {
          console.log('No active session found, redirecting to login');
          // Not logged in, redirect to login
          router.push('/login');
          return;
        }
        
        console.log('Session found, checking user type');
        
        // Check if user is driver type
        const { data: userTypeData, error: userTypeError } = await supabaseClient
          .from('user_types')
          .select('user_type')
          .eq('user_id', sessionData.session.user.id)
          .single();
          
        if (userTypeError) {
          console.error('Error fetching user type:', userTypeError);
          throw userTypeError;
        }
        
        console.log('User type:', userTypeData.user_type);
        
        if (userTypeData.user_type !== 'driver') {
          console.log('User is not a driver, redirecting to customer dashboard');
          // Wrong user type, redirect to appropriate dashboard
          router.push('/customer-dashboard');
          return;
        }
        
        console.log('Fetching driver profile data');
        
        // Get driver profile data
        const { data: profileData, error: profileError } = await supabaseClient
          .from('driver_profiles')
          .select('*')
          .eq('id', sessionData.session.user.id)
          .single();
        
        if (profileError) {
          console.error('Error fetching profile data:', profileError);
          throw profileError;
        }
        
        console.log('Profile data retrieved:', profileData);
        
        // Update user ref with profile data
        user.value = {
          driverName: profileData.driver_name,
          phoneNumber: profileData.phone_number,
          streetAddress: profileData.street_address,
          postalCode: profileData.postal_code,
          id: profileData.id
        };
        
        console.log('User data loaded successfully');
        
        // Fetch driver stats after user data is loaded
        await fetchDriverStats();

        // Request notification permission for realtime alerts
        await requestNotificationPermission();

        // Set auth token on Realtime client for authenticated RLS evaluation
        if (sessionData.session?.access_token) {
          supabaseClient.realtime.setAuth(sessionData.session.access_token);
        }

        // Setup Supabase Realtime subscription for live order updates
        setupRealtimeSubscription();

        // Load Google Maps but don't automatically fetch delivery data
        console.log('Loading Google Maps API from onMounted');
        loadGoogleMapsApi(() => {
          // Ensure we have a mapContainer reference before trying to initialize the map
          if (mapContainer.value) {
            initMap();
            // if want to auto fetch data, after map initialisation then uncomment this
            fetchDeliveryData();

            // tracking live location with device GPS
            updateDriverLocation(); // Immediate first update
            // Update location every minute for real-time tracking
            setInterval(updateDriverLocation, 60 * 1000);
          } else {
            console.warn('Map container not available yet, will initialize later');
            // Try again after a short delay to allow the DOM to render
            setTimeout(() => {
              if (mapContainer.value) {
                initMap();
                // if want to auto fetch data, after map initialisation then uncomment this
                fetchDeliveryData();

                
              } else {
                console.error('Map container still not available after delay');
              }
            }, 500);
          }
        });
        
      } catch (error) {
        console.error('Error loading user data:', error);
        errorMessage.value = 'Failed to load user data. Please try again.';
      } finally {
        isLoading.value = false;
      }
    });

    // Cleanup when component unmounts
    onUnmounted(() => {
      console.log('DriverDashboard unmounting, cleaning up...');
      cleanupRealtimeSubscription();
    });

    const toggleDropdown = (event) => {
      const dropdownMenu = event.target.closest('.dropdown').querySelector('.dropdown-menu');
      dropdownMenu.classList.toggle('show');
    };

    // Logout function
    const logout = async () => {
      try {
        isLoading.value = true;
        console.log('Logging out...');
        
        const { error } = await signOut();
        if (error) {
          console.error('Logout error:', error);
          throw error;
        }
        
        console.log('Logout successful, redirecting to home');
        // Redirect to home page after logout
        router.push('/');
      } catch (error) {
        console.error('Logout error:', error);
        errorMessage.value = 'Failed to log out. Please try again.';
      } finally {
        isLoading.value = false;
      }
    };
    
    
    
    return {
      user,
      isLoading,
      errorMessage,
      driverStats,
      logout,
      toggleDropdown,

      isFetching,
      mapContainer,
      fetchDeliveryData,

      deliveryData,
      selectOrder,
      focusOnRestaurant,
    };




  }
};
</script>


<style>
.map-container {
  height: 500px;
  margin: 20px 0;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.info-window {
  max-width: 300px;
  font-size: 14px;
}

.info-window h4 {
  margin: 0 0 10px;
  color: #2c3e50;
}

.info-window ul {
  margin: 0;
  padding-left: 20px;
}

.info-window li {
  margin: 8px 0;
}

/* Delivery Requests Styling */
.delivery-requests-container {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.restaurant-section {
  border-bottom: 1px solid #e2e5e8;
  padding-bottom: 15px;
}

.restaurant-section:last-child {
  border-bottom: none;
}

.restaurant-address {
  color: #6c757d;
  font-size: 14px;
  margin-bottom: 10px;
}

.order-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
}

.order-card {
  background-color: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.order-details h5 {
  color: #343a40;
  margin-bottom: 10px;
}

.order-details p {
  margin-bottom: 5px;
  font-size: 14px;
}
</style>