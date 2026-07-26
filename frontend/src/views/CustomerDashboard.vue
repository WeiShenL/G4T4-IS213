<template>
  <div>
    <!-- Dashboard Header -->
    <div class="dashboard-header">
      <div class="container">
        <div class="d-flex justify-content-between align-items-center">
          <router-link to="/customer-dashboard" class="dashboard-logo">
            <span>FeastFinder</span>
          </router-link>
          <div class="dashboard-user d-flex align-items-center">
            <!-- Notification Bell Icon -->
            <div class="position-relative me-3" v-if="hasPendingReservation">
              <router-link to="/accept-reallocation" class="notification-bell">
                <i class="fas fa-bell text-warning"></i>
                <span class="notification-badge"></span>
              </router-link>
            </div>
            <div class="dropdown">
              <button class="btn dropdown-toggle" type="button" id="userDropdown" @click="toggleDropdown">
                <i class="fas fa-user-circle"></i>
                <span v-if="user">{{ user.customerName }}</span>
                <span v-else>Loading...</span>
              </button>
              <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
                <li><router-link class="dropdown-item" to="/reservations"><i class="fas fa-calendar-check"></i> My Reservations</router-link></li>
                <li><router-link class="dropdown-item" to="/delivery-orders"><i class="fas fa-truck"></i> My Delivery Orders</router-link></li>
                <li v-if="hasPendingReservation"><router-link class="dropdown-item text-warning" to="/accept-reallocation"><i class="fas fa-bell"></i> Pending Table Offer</router-link></li>
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
              <h2>Welcome, <span v-if="user">{{ user.customerName }}</span><span v-else>Customer</span>!</h2>
              <p>What would you like to eat today?</p>
              <!-- Pending Reservation Alert -->
              <div v-if="hasPendingReservation" class="alert alert-warning mt-3">
                <i class="fas fa-bell me-2"></i> You have a pending table offer! 
                <router-link to="/accept-reallocation" class="alert-link">View details</router-link>
              </div>
            </div>
          </div>
        </div>
                
        <!-- Quick Actions -->
        <div class="row mb-4">
          <div class="col-12">
            <h3 class="section-heading">Quick Actions</h3>
          </div>
          <div class="col-md-3 col-sm-6 mb-3" v-for="(action, index) in quickActions" :key="index">
            <div class="action-card">
              <div class="action-icon">
                <i :class="action.icon"></i>
              </div>
              <h4>{{ action.title }}</h4>
              <router-link :to="action.link" class="action-link" @click="action.orderType">{{ action.linkText }}</router-link>
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
          <!-- Featured Restaurants -->
          <div class="row mb-4">
            <div class="col-12 mb-4">
              <h3 class="section-heading">Featured Restaurants</h3>
              <p class="section-subheading">Popular places to order from</p>
            </div>
            
            <!-- Restaurant loading state -->
            <div v-if="loadingRestaurants" class="col-12 text-center py-4">
              <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading restaurants...</span>
              </div>
              <p class="mt-2">Finding open restaurants near you...</p>
            </div>
            
            <!-- No restaurants available -->
            <div v-else-if="openRestaurants.length === 0" class="col-12 text-center py-4">
              <div class="no-restaurants">
                <i class="fas fa-store-slash mb-3"></i>
                <p>No featured restaurants at this time. Please check back later!</p>
              </div>
            </div>
            
            <!-- Restaurant gallery -->
            <div v-else class="col-12">
              <div class="restaurants-list">
                <div v-for="(restaurant, index) in openRestaurants" :key="restaurant.id" class="restaurant-row">
                  <div class="row align-items-center">
                    <!-- Restaurant Image -->
                    <div class="col-md-3">
                      <div class="restaurant-image">
                        <img :src="getRestaurantImage(index + 1)" alt="Restaurant image">
                      </div>
                    </div>
                    
                    <!-- Restaurant Info -->
                    <div class="col-md-9">
                      <div class="restaurant-details">
                        <h4 class="restaurant-name">{{ restaurant.name }}</h4>
                        <div class="restaurant-meta mb-2">
                          <span class="badge bg-light text-dark me-2">{{ restaurant.cuisine || 'Various Cuisine' }}</span>
                        </div>
                        <p class="restaurant-description">
                          {{ restaurant.description || 'A wonderful dining experience with delicious food and excellent service.' }}
                        </p>
                        
                        <!-- Reviews -->
                        <div class="reviews">
                          <div class="review">
                            <div class="review-author">{{ getReviewAuthor(index, 0) }}</div>
                            <div class="review-content">"{{ getReviewContent(index, 0) }}"</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { supabaseClient, signOut } from '@/services/supabase';
import { checkPendingReservations } from '@/services/reservationService';
import { getOpenRestaurants } from '@/services/restaurantService';

const setOrderType = async (type) => {
  // Store order_type in localStorage for temporary use
  localStorage.setItem('orderType', type);
}

export default {
  name: 'CustomerDashboard',
  setup() {
    const router = useRouter();
    const user = ref(null);
    const isLoading = ref(true);
    const errorMessage = ref('');
    const hasPendingReservation = ref(false);
    let reservationSubscription = null;
    let isRefreshingPending = false;
    const openRestaurants = ref([]);
    const loadingRestaurants = ref(false);
    
    // Restaurant image mapping (hardcoded)
    const restaurantImages = {
      1: new URL('../assets/images/restaurants/restaurant1.jpg', import.meta.url).href,
      2: new URL('../assets/images/restaurants/restaurant2.jpg', import.meta.url).href,
      3: new URL('../assets/images/restaurants/restaurant3.jpg', import.meta.url).href,
      4: new URL('../assets/images/restaurants/restaurant4.jpg', import.meta.url).href,
      5: new URL('../assets/images/restaurants/restaurant5.jpg', import.meta.url).href,
      // Default for any restaurant without matching ID
      default: new URL('../assets/images/restaurants/default-restaurant.jpg', import.meta.url).href
    };
    
    // Function to get restaurant image
    const getRestaurantImage = (id) => {
      return restaurantImages[id] || restaurantImages.default;
    };
    
    const quickActions = [
      {
        icon: 'fas fa-calendar-check',
        title: 'Book a Table',
        link: '/restaurants',
        linkText: 'Find Restaurants',
        orderType: () => setOrderType('dine_in')
      },
      {
        icon: 'fas fa-list-alt',
        title: 'View My Table Reservations',
        link: '/reservations',
        linkText: 'See Table Bookings'
      },
      {
        icon: 'fas fa-utensils',
        title: 'Order Food for Delivery',
        link: '/restaurants',
        linkText: 'Browse Restaurants',
        orderType: () => setOrderType('delivery')
      },
      {
        icon: 'fas fa-truck',
        title: 'View My Home Delivery Orders',
        link: '/delivery-orders',
        linkText: 'See Delivery Orders'
      }
    ];
    
    // toggle dropdown manually
    const toggleDropdown = (event) => {
      const dropdownMenu = event.target.closest('.dropdown').querySelector('.dropdown-menu');
      dropdownMenu.classList.toggle('show');
    };
    
    // Hardcoded review authors
    const reviewAuthors = [
      ['John D.', 'Sarah M.', 'Michael T.'],
      ['Emily L.', 'David W.', 'Jessica K.'],
      ['Robert P.', 'Michelle S.', 'Thomas G.']
    ];
    
    // Hardcoded review content
    const reviewContents = [
      [
        'The food was amazing! Definitely coming back soon.',
        'Great atmosphere and friendly staff. Highly recommend!',
        'Best dining experience I\'ve had in months!'
      ],
      [
        'The chef\'s special was incredible. Must try!',
        'Love the ambiance and the quick service.',
        'Perfect place for a romantic dinner.'
      ],
      [
        'The menu variety is impressive. Something for everyone!',
        'Fresh ingredients and authentic flavors. Loved it!',
        'Wonderful place to bring the family for dinner.'
      ]
    ];
    
    // Function to get review author
    const getReviewAuthor = (restaurantIndex, reviewIndex) => {
      return reviewAuthors[restaurantIndex % reviewAuthors.length][reviewIndex % 3];
    };
    
    // Function to get review content
    const getReviewContent = (restaurantIndex, reviewIndex) => {
      return reviewContents[restaurantIndex % reviewContents.length][reviewIndex % 3];
    };
    
    // Re-read the user's pending table offer and sync the UI to it. Safe to call
    // repeatedly - the bell, dropdown item and alert are all bound to
    // hasPendingReservation, so they follow whatever this sets.
    const refreshPendingReservation = async (userId) => {
      if (isRefreshingPending) {
        return;
      }
      isRefreshingPending = true;

      try {
        const pendingReservations = await checkPendingReservations(userId);
        console.log(`📋 Pending table offers for user: ${pendingReservations.length}`);
        hasPendingReservation.value = pendingReservations.length > 0;

        if (hasPendingReservation.value) {
          // Stash it for the accept booking page, which reads it from localStorage.
          localStorage.setItem('pendingReservation', JSON.stringify(pendingReservations[0]));
        } else {
          // Offer is gone (accepted, or passed on to someone else). Without this the
          // stale blob survives and /accept-reallocation renders an offer that no
          // longer exists.
          localStorage.removeItem('pendingReservation');
        }
      } catch (error) {
        console.error('Error checking pending reservations:', error);
        // Non-critical, leave the current state alone and try again on the next event
      } finally {
        isRefreshingPending = false;
      }
    };

    // No filter on the subscription: RLS already restricts delivered rows to this
    // user, and a server-side filter drops events silently when it doesn't match.
    const subscribeToReservationChanges = (userId) => {
      console.log('🔔 Subscribing to reservation changes for pending table offers...');

      reservationSubscription = supabaseClient
        .channel('pending-reservations')
        .on(
          'postgres_changes',
          { event: '*', schema: 'public', table: 'reservation' },
          (payload) => {
            console.log('⚡ Reservation event received via Realtime:', payload);
            // The event is only a trigger. We re-fetch rather than using payload.new
            // because /accept-reallocation expects the API's reservation shape, not
            // the raw row.
            refreshPendingReservation(userId);
          }
        )
        .subscribe((status, err) => {
          // SUBSCRIBED alone doesn't mean events will flow - CHANNEL_ERROR here is how
          // a missing publication entry or a broken realtime schema surfaces.
          console.log(`🔔 Reservation channel status: ${status}`, err || '');
        });
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
        
        // Check if user is customer type
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
        
        if (userTypeData.user_type !== 'customer') {
          console.log('User is not a customer, redirecting to driver dashboard');
          // Wrong user type, redirect to appropriate dashboard
          router.push('/driver-dashboard');
          return;
        }
        
        console.log('Fetching customer profile data');
        
        // Get customer profile data
        const { data: profileData, error: profileError } = await supabaseClient
          .from('customer_profiles')
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
          customerName: profileData.customer_name,
          phoneNumber: profileData.phone_number,
          streetAddress: profileData.street_address,
          postalCode: profileData.postal_code,
          id: profileData.id
        };
        
        // Store user information in `local`Storage for other components
        localStorage.setItem('user_id', profileData.id);
        localStorage.setItem('user_name', profileData.customer_name);
        localStorage.setItem('user_phone', profileData.phone_number);
        
        console.log('User data loaded successfully');
        
        // Check for pending reservations
        await refreshPendingReservation(profileData.id);

        // Live updates: a cancellation reallocates the reservation row to the next
        // waitlisted user, so the offer arrives as an UPDATE on public.reservation.
        // setAuth must run first or Realtime evaluates RLS as anon and sends nothing.
        supabaseClient.realtime.setAuth(sessionData.session.access_token);
        subscribeToReservationChanges(profileData.id);

        // Fetch open restaurants
        try {
          loadingRestaurants.value = true;
          const restaurants = await getOpenRestaurants();
          openRestaurants.value = restaurants;
        } catch (error) {
          console.error('Error fetching open restaurants:', error);
          // Non-critical error, continue loading dashboard
        } finally {
          loadingRestaurants.value = false;
        }
      } catch (error) {
        console.error('Error loading user data:', error);
        errorMessage.value = 'Failed to load user data. Please try again.';
      } finally {
        isLoading.value = false;
      }
    });

    onUnmounted(() => {
      if (reservationSubscription) {
        supabaseClient.removeChannel(reservationSubscription);
        reservationSubscription = null;
      }
    });

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
        
        // Clear any stored user data
        localStorage.removeItem('user_id');
        localStorage.removeItem('user_name');
        localStorage.removeItem('user_phone');
        localStorage.removeItem('pendingReservation');
        
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
      quickActions,
      hasPendingReservation,
      openRestaurants,
      loadingRestaurants,
      getRestaurantImage,
      logout,
      toggleDropdown,
      getReviewAuthor,
      getReviewContent,
      router
    };
  }
};
</script>

<style scoped>
.notification-bell {
  font-size: 1.5rem;
  color: #ffc107;
  display: block;
  position: relative;
}

.notification-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #dc3545;
  display: block;
}

.no-restaurants {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px;
  background: #f9f9f9;
  border-radius: 8px;
  color: #777;
}

.no-restaurants i {
  font-size: 48px;
  color: #ccc;
}

/* Row-based Restaurant Styling */
.restaurants-list {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.restaurant-row {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  padding: 20px;
}

.restaurant-row:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
}

.restaurant-image {
  width: 100%;
  height: 160px;
  overflow: hidden;
  border-radius: 8px;
  cursor: pointer;
}

.restaurant-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.restaurant-row:hover .restaurant-image img {
  transform: scale(1.05);
}

.restaurant-details {
  padding: 0 15px;
}

.restaurant-name {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.restaurant-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.restaurant-description {
  margin: 10px 0;
  color: #666;
  font-size: 14px;
}

.reviews {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 15px;
  margin-top: 10px;
}

.review {
  border-left: 3px solid #ff6b6b;
  padding-left: 15px;
}

.review-author {
  font-weight: 600;
  font-size: 14px;
  color: #333;
  margin-bottom: 5px;
}

.review-content {
  font-style: italic;
  color: #555;
  font-size: 14px;
}
</style>