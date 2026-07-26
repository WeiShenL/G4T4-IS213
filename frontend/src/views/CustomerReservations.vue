<template>
    <div>
      <!-- Dashboard Header -->
      <div class="dashboard-header">
        <div class="container">
          <div class="d-flex justify-content-between align-items-center">
            <router-link to="/customer-dashboard" class="dashboard-logo">
              <span>FeastFinder</span>
            </router-link>
            <div class="dashboard-user">
              <div class="dropdown">
                <button class="btn dropdown-toggle" type="button" id="userDropdown" @click="toggleDropdown">
                  <i class="fas fa-user-circle"></i>
                  <span v-if="user">{{ user.customerName }}</span>
                  <span v-else>Loading...</span>
                </button>
                <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
                  <li><router-link class="dropdown-item" to="/customer-dashboard"><i class="fas fa-home"></i> Dashboard</router-link></li>
                  <li><router-link class="dropdown-item" to="/reservations"><i class="fas fa-calendar-check"></i> My Reservations</router-link></li>
                  <li><router-link class="dropdown-item" to="/delivery-orders"><i class="fas fa-truck"></i> My Delivery Orders</router-link></li>
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item" href="#" @click.prevent="logout"><i class="fas fa-sign-out-alt"></i> Logout</a></li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Reservations Content -->
      <div class="dashboard-container">
        <div class="container">
          <!-- Page Title -->
          <div class="row mb-4">
            <div class="col-12">
              <div class="welcome-card">
                <h2>My Reservations</h2>
                <p>View your restaurant reservations</p>
              </div>
            </div>
          </div>
          
          <!-- Loading State -->
          <div v-if="isLoading" class="loading-container">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p>Loading your reservations...</p>
          </div>
          
          <!-- Error Message -->
          <div v-if="errorMessage" class="alert alert-danger" role="alert">
            {{ errorMessage }}
          </div>
          
          <!-- Cancellation Success Banner (Top of Page) -->
          <div v-if="showTopCancellationBanner" class="alert alert-success border-0 shadow-sm mb-4" role="alert">
            <h4 class="alert-heading mb-2"><i class="fas fa-check-circle me-2"></i>Reservation Cancelled & Refund Issued!</h4>
            <p class="mb-2">Your booking has been cancelled and refunded via Stripe.</p>
            
            <div class="alert alert-info border-0 shadow-sm mt-2 mb-0 bg-light text-dark">
              <div class="d-flex align-items-center mb-1">
                <i class="fas fa-paper-plane text-info me-2 fs-5"></i>
                <strong>Cancellation Notice Email Dispatched!</strong>
              </div>
              <small class="text-muted d-block">
                A cancellation & refund email notification has been dispatched via Resend API. 
                <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to the developer's testing inbox).</em>
              </small>
            </div>
          </div>
          
          <!-- Reservations Table -->
          <div v-if="!isLoading && reservations.length > 0" class="card mb-4">
            <div class="card-body">
              <div class="table-responsive">
                <table class="table table-striped">
                  <thead>
                    <tr>
                      <th>Restaurant</th>
                      <th>Date</th>
                      <th>Time</th>
                      <th>Party Size</th>
                      <th>Table No.</th>
                      <th>Price</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="reservation in reservations" :key="reservation.reservation_id">
                      <td>{{ getRestaurantName(reservation.restaurant_id) }}</td>
                      <td>{{ formatDate(reservation.time) }}</td>
                      <td>{{ formatTime(reservation.time) }}</td>
                      <td>{{ reservation.count }}</td>
                      <td>{{ reservation.table_no || 'TBD' }}</td>
                      <td>${{ reservation.price ? reservation.price.toFixed(2) : '0.00' }}</td>
                      <td>
                        <span 
                          class="badge"
                          :class="getStatusClass(reservation.status)"
                        >
                          {{ reservation.status }}
                        </span>
                      </td>
                      <td>
                        <button 
                          class="btn btn-sm btn-outline-danger"
                          @click="cancelReservation(reservation)"
                          :disabled="reservation.status === 'Cancelled' || reservation.status === 'Completed'"
                        >
                          Cancel Reservation
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          
          <!-- No Reservations -->
          <div v-if="!isLoading && reservations.length === 0" class="empty-state">
            <i class="fas fa-calendar-alt"></i>
            <p>You don't have any reservations yet.</p>
            <small>Book a table at your favorite restaurant to see it here.</small>
            <div class="mt-3">
              <router-link to="/restaurants" class="btn btn-primary">
                Browse Restaurants
              </router-link>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Cancellation Confirmation Modal -->
      <div class="modal fade" id="cancellationModal" tabindex="-1" aria-labelledby="cancellationModalLabel" aria-hidden="true">
        <div class="modal-dialog">
          <div class="modal-content" v-if="selectedReservation">
            <div class="modal-header">
              <h5 class="modal-title" id="cancellationModalLabel">Confirm Cancellation</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" :disabled="isProcessingCancellation"></button>
            </div>
            
            <!-- Loading State -->
            <div v-if="isProcessingCancellation" class="modal-body text-center p-4">
              <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Processing cancellation...</span>
              </div>
              <p>Processing your cancellation...</p>
              <small class="text-muted">This may take a moment to complete</small>
            </div>
            
            <!-- Success State -->
            <div v-else-if="cancellationSuccess" class="modal-body text-center p-4">
              <div class="mb-3 text-success">
                <i class="fas fa-check-circle fa-3x"></i>
              </div>
              <h4 class="text-success">Cancellation Successful!</h4>
              <p>Your reservation has been cancelled and your refund is being processed.</p>
              
              <!-- Resend Email Notification Banner -->
              <div class="alert alert-info border-0 shadow-sm mt-3 bg-light text-dark text-start">
                <div class="d-flex align-items-center mb-1">
                  <i class="fas fa-paper-plane text-info me-2 fs-5"></i>
                  <strong>Cancellation Notice Email Dispatched!</strong>
                </div>
                <small class="text-muted d-block">
                  A cancellation & refund email notification has been dispatched via Resend API. 
                  <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to the developer's testing inbox).</em>
                </small>
              </div>
            </div>
            
            <!-- Error State -->
            <div v-else-if="cancellationError" class="modal-body">
              <div class="alert alert-danger mb-3">
                <i class="fas fa-exclamation-circle me-2"></i>
                {{ cancellationError }}
              </div>
              <p>Are you sure you want to cancel your reservation at <strong>{{ getRestaurantName(selectedReservation.restaurant_id) }}</strong> on {{ formatDate(selectedReservation.time) }} at {{ formatTime(selectedReservation.time) }}?</p>
              <p class="text-danger">This action cannot be undone.</p>
            </div>
            
            <!-- Confirmation State (Default) -->
            <div v-else class="modal-body">
              <p>Are you sure you want to cancel your reservation at <strong>{{ getRestaurantName(selectedReservation.restaurant_id) }}</strong> on {{ formatDate(selectedReservation.time) }} at {{ formatTime(selectedReservation.time) }}?</p>
              <p class="text-danger">This action cannot be undone.</p>
            </div>
            
            <div class="modal-footer" v-if="!isProcessingCancellation && !cancellationSuccess">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Keep Reservation</button>
              <button type="button" class="btn btn-danger" @click="confirmCancellation">Confirm Cancellation</button>
            </div>
          </div>
        </div>
      </div>
    </div>
</template>
  
<script>
import { ref, onMounted, onUnmounted } from 'vue'; 
import { useRouter } from 'vue-router';
import { supabaseClient, signOut, getCurrentUser } from '@/services/supabase';
import { getUserReservations, getUserWaitlist } from '@/services/reservationService';
import { getAllRestaurants } from '@/services/restaurantService';
import { initStripe, processRefund } from '@/services/stripeService';
import { Modal } from 'bootstrap'; 

const API_GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL || 'http://localhost:8000';
const CANCEL_BOOKING_PATH = '/api/cancel';

export default {
  name: 'CustomerReservations',
  setup() {
    // Setup CustomerReservations component state
    const router = useRouter();
    const user = ref(null);
    const reservations = ref([]);
    const restaurants = ref([]);
    const isLoading = ref(true);
    const errorMessage = ref('');
    const selectedReservation = ref(null);
    const cancellationModalInstance = ref(null); 
    const isProcessingCancellation = ref(false);
    const cancellationSuccess = ref(false);
    const cancellationError = ref('');
    const showTopCancellationBanner = ref(false);

    // toggle dropdown manually
    const toggleDropdown = (event) => {
      const dropdownMenu = event.target.closest('.dropdown').querySelector('.dropdown-menu');
      dropdownMenu.classList.toggle('show');
    };

    // bootstrap modal instance, modal class
    const initModal = () => {
      try {
        const modalElement = document.getElementById('cancellationModal');
        if (modalElement) {
          cancellationModalInstance.value = new Modal(modalElement); 
        } else {
          console.warn('Modal element (#cancellationModal) not found during initial mount.');
        }
      } catch (error) {
        console.error('Error initializing Bootstrap modal:', error);
        errorMessage.value = 'Could not initialize the cancellation dialog.';
      }
    };

    // load data when the component mounts, initialise modal
    onMounted(async () => {
      initModal(); 
      try {
        await loadUserData(); 
        if (user.value) {
          await Promise.all([loadRestaurants(), loadReservations()]);
        }
      } catch (error) {
        console.error('Error during initialization:', error);
        errorMessage.value = 'An error occurred while loading the page. Please try again.';
      } finally {
        isLoading.value = false;
      }
    });

    // remove modal
    onUnmounted(() => {
      cancellationModalInstance.value?.dispose(); 
    });
    
    // load user data
    const loadUserData = async () => {
      try {
        // logged in>?
        const currentUser = await getCurrentUser();
        
        if (!currentUser) {
          // Not logged in, redirect to login
          router.push('/login');
          return;
        }
        
        // Get customer profile data
        const { data: profileData, error: profileError } = await supabaseClient
          .from('customer_profiles')
          .select('*')
          .eq('id', currentUser.id)
          .single();
        
        if (profileError) {
          console.error('Error fetching profile data:', profileError);
          throw profileError;
        }
        
        // Update user ref with profile data
        user.value = {
          customerName: profileData.customer_name,
          phoneNumber: profileData.phone_number,
          streetAddress: profileData.street_address,
          postalCode: profileData.postal_code,
          id: currentUser.id
        };
      } catch (error) {
        console.error('Error loading user data:', error);
        throw error;
      }
    };
    
    // Load restaurants data for names
    const loadRestaurants = async () => {
      try {
        const restaurantsData = await getAllRestaurants();
        restaurants.value = restaurantsData;
      } catch (error) {
        console.error('Error loading restaurants:', error);
        // Not fatal, so just log the error
      }
    };
    
    // Load user's reservations and waitlist entries in parallel (API Composition)
    const loadReservations = async () => {
      try {
        if (!user.value || !user.value.id) {
          console.warn('User ID not available yet, skipping reservation loading');
          return;
        }
        
        console.log('Loading reservations & waitlist for user ID:', user.value.id);
        
        const [userReservations, userWaitlist] = await Promise.all([
          getUserReservations(user.value.id.toString()).catch(() => []),
          getUserWaitlist(user.value.id.toString()).catch(() => [])
        ]);

        const formattedWaitlist = (userWaitlist || []).map(item => ({
          reservation_id: `w-${item.Id || item.waitlist_id}`,
          restaurant_id: item.restaurant_id,
          time: item.time || item.timestamp_added,
          count: 1,
          table_no: 'Waitlist Queue',
          price: 0,
          status: 'Waitlisted',
          isWaitlist: true
        }));
        
        reservations.value = [...(userReservations || []), ...formattedWaitlist];
        console.log('Loaded merged reservations & waitlist:', reservations.value);
      } catch (error) {
        console.error('Error loading reservations:', error);
        errorMessage.value = 'Failed to load your reservations. Please try again later.';
      }
    };

    
    // Format date from ISO string
    const formatDate = (isoString) => {
      if (!isoString) return 'N/A';
      const date = new Date(isoString);
      return date.toLocaleDateString();
    };
    
    // Format time from ISO string
    const formatTime = (isoString) => {
      if (!isoString) return 'N/A';
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };
    
    // Get restaurant name from ID
    const getRestaurantName = (restaurantId) => {
      const restaurant = restaurants.value.find(r => r.restaurant_id === restaurantId);
      return restaurant ? restaurant.name : `Restaurant #${restaurantId}`;
    };
    
    // Get CSS class for status badge --> maybe dunnit so many
    const getStatusClass = (status) => {
      switch (status) {
        case 'Booked':
          return 'bg-primary';
        case 'Confirmed':
          return 'bg-success';
        case 'Waitlisted':
          return 'bg-warning text-dark';
        case 'Cancelled':
          return 'bg-danger';
        case 'Completed':
          return 'bg-info';
        default:
          return 'bg-secondary';
      }
    };
    
    // Handle reservation cancellation
    const cancelReservation = (reservation) => {
      selectedReservation.value = reservation;
      cancellationError.value = '';
      cancellationSuccess.value = false;
      isProcessingCancellation.value = false;

      if (cancellationModalInstance.value) {
        cancellationModalInstance.value.show();
      } else {
        console.warn("Modal instance not found. Attempting re-initialization.");
        initModal();
        if (cancellationModalInstance.value) {
          cancellationModalInstance.value.show();
        } else {
          errorMessage.value = 'Cancellation dialog failed to open. Please refresh.';
          console.error("Modal instance could not be created or found.");
        }
      }
    };
    
    // Confirm cancellation
    const confirmCancellation = async () => {
      if (!selectedReservation.value) {
        return;
      }
      
      try {
        // Set loading state
        isProcessingCancellation.value = true;
        cancellationError.value = '';
        
        console.log('Starting cancellation process for reservation:', selectedReservation.value.reservation_id);
        
        // Call the cancel_booking microservice
        const response = await fetch(`${API_GATEWAY_URL}${CANCEL_BOOKING_PATH}/${selectedReservation.value.reservation_id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `Failed to cancel reservation: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Cancellation response:', data);
        
        // Note: cancel_booking microservice already executed the Stripe refund atomically on the backend.
        console.log('Cancellation & refund completed successfully by microservice:', data);
        
        // Update UI to show success
        cancellationSuccess.value = true;
        showTopCancellationBanner.value = true;
        
        // Hide modal after a short delay
        setTimeout(() => {
          if (cancellationModalInstance.value) {
            cancellationModalInstance.value.hide();
          }
          
          // Reload reservations
          loadReservations();
          
          // Reset cancellation state after modal is hidden
          setTimeout(() => {
            cancellationSuccess.value = false;
            isProcessingCancellation.value = false;
            selectedReservation.value = null;
          }, 500);
        }, 2000);
        
      } catch (error) {
        console.error('Error during cancellation:', error);
        cancellationError.value = error.message || 'An error occurred during cancellation';
        isProcessingCancellation.value = false;
            setTimeout(() => {
          loadReservations();
        }, 2000);
      }
    };
    
    // Logout function
    const logout = async () => {
      try {
        isLoading.value = true;
        const { error } = await signOut();
        if (error) throw error;
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
      reservations,
      isLoading,
      errorMessage,
      selectedReservation,
      isProcessingCancellation,
      cancellationSuccess,
      cancellationError,
      showTopCancellationBanner,
      formatDate,
      formatTime,
      getRestaurantName,
      getStatusClass,
      cancelReservation,
      confirmCancellation,
      logout,
      toggleDropdown
    };
  }
};
</script>

<style scoped>
.badge {
  padding: 6px 10px;
}

/* Add some button styling */
.btn-outline-danger {
  transition: all 0.3s ease;
}

.btn-outline-danger:hover {
  background-color: #dc3545;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 2px 5px rgba(220, 53, 69, 0.3);
}
</style>