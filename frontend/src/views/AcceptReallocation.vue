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
                <button class="btn dropdown-toggle" type="button" id="userDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                  <i class="fas fa-user-circle"></i>
                  <span v-if="user">{{ user.customerName }}</span>
                  <span v-else>Loading...</span>
                </button>
                <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
                  <li><router-link class="dropdown-item" to="/customer-dashboard"><i class="fas fa-home"></i> Dashboard</router-link></li>
                  <li><router-link class="dropdown-item" to="/reservations"><i class="fas fa-calendar-check"></i> My Reservations</router-link></li>
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item" href="#" @click.prevent="logout"><i class="fas fa-sign-out-alt"></i> Logout</a></li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Accept Booking Content -->
      <div class="dashboard-container">
        <div class="container">
          <div class="row justify-content-center">
            <div class="col-lg-8">
              <!-- Page Title -->
              <div class="welcome-card mb-4">
                <h2>Table Offer Available!</h2>
                <p>Someone has cancelled their reservation and you're next in the waitlist</p>
              </div>
              
              <!-- Loading State -->
              <div v-if="isLoading" class="loading-container">
                <div class="spinner-border text-primary" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
                <p>Loading table details...</p>
              </div>
              
              <!-- Error Message -->
              <div v-if="errorMessage" class="alert alert-danger" role="alert">
                {{ errorMessage }}
              </div>
              
              <!-- Success Message (Accepted) -->
              <div v-if="bookingAccepted" class="card mb-4">
                <div class="card-body text-center p-5">
                  <div class="mb-4">
                    <i class="fas fa-check-circle text-success fa-4x"></i>
                  </div>
                  <h3 class="mb-3">Table Booked Successfully!</h3>
                  <p class="mb-4">Your reservation has been confirmed. We look forward to seeing you soon!</p>
                  
                  <!-- Resend Email Notification Banner -->
                  <div class="alert alert-info border-0 shadow-sm mb-4 text-start bg-light text-dark">
                    <div class="d-flex align-items-center mb-1">
                      <i class="fas fa-paper-plane text-success me-2 fs-5"></i>
                      <strong>Table Offer Accepted Email Dispatched!</strong>
                    </div>
                    <small class="text-muted d-block">
                      An automated confirmation email has been dispatched via Resend API. 
                      <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to my testing inbox).</em>
                    </small>
                  </div>

                  <div class="d-flex justify-content-center">
                    <router-link to="/reservations" class="btn btn-primary me-2">
                      <i class="fas fa-calendar-check me-2"></i>View My Reservations
                    </router-link>
                    <router-link to="/customer-dashboard" class="btn btn-outline-primary">
                      <i class="fas fa-home me-2"></i>Back to Dashboard
                    </router-link>
                  </div>
                </div>
              </div>
              
              <!-- Decline Success Message (Declined) -->
              <div v-if="bookingDeclined" class="card mb-4">
                <div class="card-body text-center p-5">
                  <div class="mb-4">
                    <i class="fas fa-times-circle text-muted fa-4x"></i>
                  </div>
                  <h3 class="mb-3">Table Offer Declined</h3>
                  <p class="mb-4">The table offer has been declined and will be offered to the next customer in the waitlist.</p>
                  
                  <!-- Resend Email Notification Banner -->
                  <div class="alert alert-info border-0 shadow-sm mb-4 text-start bg-light text-dark">
                    <div class="d-flex align-items-center mb-1">
                      <i class="fas fa-paper-plane text-info me-2 fs-5"></i>
                      <strong>Table Offer Declined Email Dispatched!</strong>
                    </div>
                    <small class="text-muted d-block">
                      A table offer decline notification email has been dispatched via Resend API. 
                      <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to my testing inbox).</em>
                    </small>
                  </div>

                  <div class="d-flex justify-content-center">
                    <router-link to="/customer-dashboard" class="btn btn-primary me-2">
                      <i class="fas fa-home me-2"></i>Back to Dashboard
                    </router-link>
                    <router-link to="/restaurants" class="btn btn-outline-primary">
                      <i class="fas fa-utensils me-2"></i>Browse Restaurants
                    </router-link>
                  </div>
                </div>
              </div>
              
              <!-- Booking Offer Details -->
              <div v-if="!isLoading && !bookingAccepted && !bookingDeclined && reservation" class="card mb-4">
                <div class="card-header bg-warning text-dark">
                  <h3 class="mb-0"><i class="fas fa-exclamation-circle me-2"></i>Table Offer</h3>
                </div>
                <div class="card-body">
                  <div class="reservation-details">
                    <div class="row mb-4">
                      <div class="col-md-6">
                        <div class="detail-item">
                          <span class="detail-label">Restaurant:</span>
                          <span class="detail-value">{{ restaurantName }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">Table Number:</span>
                          <span class="detail-value">{{ reservation.table_no }}</span>
                        </div>
                      </div>
                      <div class="col-md-6">
                        <div class="detail-item">
                          <span class="detail-label">Status:</span>
                          <span class="detail-value status-badge status-pending">{{ reservation.status }}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div class="alert alert-info mb-4">
                      <i class="fas fa-info-circle me-2"></i>
                      <strong>This offer is available only for you!</strong> Someone cancelled their reservation and you are next in line on our waitlist.
                    </div>

                    <!-- Resend Email Notification Banner -->
                    <div class="alert alert-info border-0 shadow-sm mb-4 bg-light text-dark">
                      <div class="d-flex align-items-center mb-1">
                        <i class="fas fa-paper-plane text-warning me-2 fs-5"></i>
                        <strong>Table Offer Notification Email Dispatched!</strong>
                      </div>
                      <small class="text-muted d-block">
                        A table reallocation offer notification email has been dispatched via Resend API. 
                        <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to my testing inbox).</em>
                      </small>
                    </div>
                    
                    <!-- Booking Form -->
                    <h4 class="mb-3">Booking Details</h4>
                    <div class="row mb-3">
                      <div class="col-md-4">
                        <div class="form-group mb-3">
                          <label for="partySize" class="form-label">Number of People</label>
                          <input 
                            type="number" 
                            class="form-control" 
                            id="partySize" 
                            v-model="partySize" 
                            min="1" 
                            max="20" 
                            required
                          >
                        </div>
                      </div>
                      <div class="col-md-4">
                        <div class="form-group mb-3">
                          <label for="bookingDate" class="form-label">Date</label>
                          <input
                            type="date"
                            class="form-control"
                            id="bookingDate"
                            v-model="bookingDate"
                            required
                          >
                        </div>
                      </div>
                      <div class="col-md-4">
                        <div class="form-group mb-3">
                          <label for="bookingTime" class="form-label">Time</label>
                          <input
                            type="time"
                            class="form-control"
                            id="bookingTime"
                            v-model="bookingTime"
                            required
                          >
                        </div>
                      </div>
                    </div>
                    
                    <div class="text-center">
                      <div v-if="isAccepting" class="d-flex justify-content-center mb-3 align-items-center">
                        <div class="spinner-border text-primary me-2" role="status">
                          <span class="visually-hidden">Processing...</span>
                        </div>
                        <span>Please wait...</span>
                      </div>

                      <button
                        class="btn btn-lg btn-success me-3"
                        @click="acceptBooking"
                        :disabled="isAccepting || !partySize || !bookingDate || !bookingTime"
                      >
                        <i class="fas fa-check-circle me-2"></i>
                        Accept & Book This Table
                      </button>

                      <button
                        class="btn btn-lg btn-outline-danger"
                        @click="declineBooking"
                        :disabled="isAccepting"
                      >
                        <i class="fas fa-times-circle me-2"></i>
                        Decline Offer
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- No Reservation Available -->
              <div v-if="!isLoading && !reservation && !bookingAccepted" class="card">
                <div class="card-body text-center p-5">
                  <div class="mb-4">
                    <i class="fas fa-exclamation-circle text-warning fa-4x"></i>
                  </div>
                  <h3 class="mb-3">No Table Offers Available</h3>
                  <p class="mb-4">There are currently no table offers available for you. Please check back later or make a new reservation.</p>
                  <div class="d-flex justify-content-center">
                    <router-link to="/restaurants" class="btn btn-primary me-2">
                      <i class="fas fa-utensils me-2"></i>Browse Restaurants
                    </router-link>
                    <router-link to="/customer-dashboard" class="btn btn-outline-primary">
                      <i class="fas fa-home me-2"></i>Back to Dashboard
                    </router-link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Decline Confirmation Modal -->
      <div class="modal fade" id="declineModal" tabindex="-1" aria-labelledby="declineModalLabel" aria-hidden="true">
        <div class="modal-dialog">
          <div class="modal-content" v-if="reservation">
            <div class="modal-header">
              <h5 class="modal-title" id="declineModalLabel">Confirm Decline</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" :disabled="isProcessingDecline"></button>
            </div>

            <!-- Loading State -->
            <div v-if="isProcessingDecline" class="modal-body text-center p-4">
              <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Processing decline...</span>
              </div>
              <p>Processing your decline request...</p>
              <small class="text-muted">This may take a moment to complete</small>
            </div>

            <!-- Success State -->
            <div v-else-if="declineSuccess" class="modal-body text-center p-4">
              <div class="mb-3 text-success">
                <i class="fas fa-check-circle fa-3x"></i>
              </div>
              <h4 class="text-success">Table Offer Declined!</h4>
              <p>The table offer has been declined and will be offered to the next customer in the waitlist.</p>
              
              <!-- Resend Email Notification Banner -->
              <div class="alert alert-info border-0 shadow-sm mt-3 bg-light text-dark text-start">
                <div class="d-flex align-items-center mb-1">
                  <i class="fas fa-paper-plane text-info me-2 fs-5"></i>
                  <strong>Table Offer Declined Email Dispatched!</strong>
                </div>
                <small class="text-muted d-block">
                  A table offer decline notification email has been dispatched via Resend API. 
                  <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to my testing inbox).</em>
                </small>
              </div>
            </div>

            <!-- Error State -->
            <div v-else-if="declineError" class="modal-body">
              <div class="alert alert-danger mb-3">
                <i class="fas fa-exclamation-circle me-2"></i>
                {{ declineError }}
              </div>
              <p>Are you sure you want to decline this table offer at <strong>{{ restaurantName }}</strong>?</p>
              <p class="text-danger">This action cannot be undone.</p>
            </div>

            <!-- Confirmation State (Default) -->
            <div v-else class="modal-body">
              <p>Are you sure you want to decline this table offer at <strong>{{ restaurantName }}</strong>?</p>
              <p class="text-danger">This table will be offered to the next customer in the waitlist.</p>
            </div>

            <div class="modal-footer" v-if="!isProcessingDecline && !declineSuccess">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Keep Offer</button>
              <button type="button" class="btn btn-danger" @click="confirmDecline">Confirm Decline</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import { ref, onMounted, computed } from 'vue';
  import { useRouter } from 'vue-router';
  import { getCurrentUser, signOut } from '@/services/supabase';
  import { getRestaurantById } from '@/services/restaurantService';
  import { acceptReallocation, cancelReallocation } from '@/services/reservationService';
  import { Modal } from 'bootstrap';
  
  export default {
    name: 'AcceptBooking',
    setup() {
      const router = useRouter();
      const user = ref(null);
      const reservation = ref(null);
      const restaurantData = ref(null);
      const restaurantName = ref('');
      const partySize = ref(2); // Default to 2 people
      const bookingDate = ref('');
      const bookingTime = ref('');
      const isLoading = ref(true);
      const isAccepting = ref(false);
      const errorMessage = ref('');
      const bookingAccepted = ref(false);
      const bookingDeclined = ref(false);

      // Decline modal states
      const declineModalInstance = ref(null);
      const isProcessingDecline = ref(false);
      const declineSuccess = ref(false);
      const declineError = ref('');

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

      // Initialize modals
      const initModals = () => {
        try {
          const declineModalElement = document.getElementById('declineModal');
          if (declineModalElement) {
            declineModalInstance.value = new Modal(declineModalElement);
          }
        } catch (error) {
          console.error('Error initializing Bootstrap modal:', error);
          errorMessage.value = 'Could not initialize the decline dialog.';
        }
      };

      // Load data when component mounts
      onMounted(async () => {
        try {
          // Load user data
          await loadUserData();
          
          // Check for pending reservation
          const pendingReservationStr = localStorage.getItem('pendingReservation');
          if (pendingReservationStr) {
            reservation.value = JSON.parse(pendingReservationStr);
            
            // Get restaurant data
            if (reservation.value.restaurant_id) {
              await loadRestaurantData(reservation.value.restaurant_id);
            }
            
            // Set default date and time for booking (today and current time + 1 hour)
            const now = new Date();
            bookingDate.value = now.toISOString().split('T')[0];
            
            now.setHours(now.getHours() + 1);
            const hours = now.getHours().toString().padStart(2, '0');
            const minutes = now.getMinutes().toString().padStart(2, '0');
            bookingTime.value = `${hours}:${minutes}`;
          }

          // Initialize the modal
          initModals();
        } catch (error) {
          console.error('Error during initialization:', error);
          errorMessage.value = 'An error occurred while loading the page. Please try again.';
        } finally {
          isLoading.value = false;
        }
      });
      
      // Load user data
      const loadUserData = async () => {
        try {
          const currentUser = await getCurrentUser();
          
          if (!currentUser) {
            // Not logged in, redirect to login
            router.push('/login');
            return;
          }
          
          // Try to get from localStorage first
          const userName = localStorage.getItem('user_name');
          const userPhone = localStorage.getItem('user_phone');
          const userId = localStorage.getItem('user_id');
          
          if (userName && userPhone && userId) {
            user.value = {
              id: userId,
              customerName: userName,
              phoneNumber: userPhone
            };
            return;
          }
          
          // If not in localStorage, fetch from Supabase
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
            id: profileData.id
          };
          
          // Store user information in localStorage
          localStorage.setItem('user_id', profileData.id);
          localStorage.setItem('user_name', profileData.customer_name);
          localStorage.setItem('user_phone', profileData.phone_number);
        } catch (error) {
          console.error('Error loading user data:', error);
          throw error;
        }
      };
      
      // Load restaurant data
      const loadRestaurantData = async (restaurantId) => {
        try {
          // Get restaurant details
          restaurantData.value = await getRestaurantById(restaurantId);
          if (restaurantData.value) {
            restaurantName.value = restaurantData.value.name;
          } else {
            restaurantName.value = `Restaurant #${restaurantId}`;
          }
        } catch (error) {
          console.error('Error loading restaurant data:', error);
          // Non-critical error, continue loading page
          restaurantName.value = `Restaurant #${restaurantId}`;
        }
      };
      
      // Accept booking
      const acceptBooking = async () => {
        if (isAccepting.value) return;
        
        try {
          isAccepting.value = true;
          errorMessage.value = '';
          
          if (!partySize.value) {
            errorMessage.value = 'Please specify the number of people for your reservation';
            isAccepting.value = false;
            return;
          }
          
          if (!bookingDate.value || !bookingTime.value) {
            errorMessage.value = 'Please specify both date and time for your reservation';
            isAccepting.value = false;
            return;
          }
          
          // Get user data from session
          if (!user.value || !user.value.id) {
            errorMessage.value = 'User information is missing. Please log in again.';
            isAccepting.value = false;
            return;
          }
          
          // Prepare date and time for the booking
          const bookingDateTime = new Date(`${bookingDate.value}T${bookingTime.value}`);
          
          // Prepare the data for accepting the reservation
          // toISOString converts time to UTC not UTC+8 so need to run thru conversion done at frontend
          const acceptData = {
            reservation_id: reservation.value.reservation_id,
            user_id: user.value.id,
            username: user.value.customerName,
            phone_number: user.value.phoneNumber,
            count: partySize.value,
            booking_time: new Date(bookingDateTime.getTime() - (bookingDateTime.getTimezoneOffset() * 60000)).toISOString()
          };
          
          console.log('Accepting reservation with data:', acceptData);
          
          // Call the API to accept the reservation
          const result = await acceptReallocation(acceptData);
          
          // Handle successful acceptance
          bookingAccepted.value = true;
          
          // Clear the pending reservation from localStorage
          localStorage.removeItem('pendingReservation');
          
          // Redirect to reservations after 3 seconds (not dashboard bruhh)
          setTimeout(() => {
            router.push('/reservations');
          }, 3000);
          
        } catch (error) {
          console.error('Error accepting booking:', error);
          errorMessage.value = error.message || 'Failed to accept booking. Please try again.';
        } finally {
          isAccepting.value = false;
        }
      };

      // Decline booking - show confirmation modal
      const declineBooking = () => {
        declineError.value = '';
        declineSuccess.value = false;
        isProcessingDecline.value = false;

        if (declineModalInstance.value) {
          declineModalInstance.value.show();
        } else {
          console.warn("Modal instance not found. Attempting re-initialization.");
          initModals();
          if (declineModalInstance.value) {
            declineModalInstance.value.show();
          } else {
            errorMessage.value = 'Decline dialog failed to open. Please refresh.';
            console.error("Modal instance could not be created or found.");
          }
        }
      };

      // Confirm decline
      const confirmDecline = async () => {
        if (!reservation.value) {
          return;
        }

        try {
          isProcessingDecline.value = true;
          declineError.value = '';

          console.log('Starting decline process for reservation:', reservation.value.reservation_id);

          // Call the cancelReallocation API
          const result = await cancelReallocation(reservation.value.reservation_id);

          if (!result.success) {
            throw new Error(result.message || 'Failed to decline table offer');
          }

          // Update UI to show decline card
          declineSuccess.value = true;
          bookingDeclined.value = true;

          // Hide modal immediately and clear pending reservation
          if (declineModalInstance.value) {
            declineModalInstance.value.hide();
          }
          localStorage.removeItem('pendingReservation');

        } catch (error) {
          console.error('Error during decline process:', error);
          declineError.value = error.message || 'An error occurred while declining the offer';
          isProcessingDecline.value = false;
        }
      };

      // Logout function
      const logout = async () => {
        try {
          isLoading.value = true;
          await signOut();
          
          // Clear any stored user data
          localStorage.removeItem('user_id');
          localStorage.removeItem('user_name');
          localStorage.removeItem('user_phone');
          localStorage.removeItem('pendingReservation');
          
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
        reservation,
        restaurantName,
        partySize,
        bookingDate,
        bookingTime,
        isLoading,
        isAccepting,
        errorMessage,
        bookingAccepted,
        bookingDeclined,
        formatDate,
        formatTime,
        acceptBooking,
        declineBooking,
        confirmDecline,
        isProcessingDecline,
        declineSuccess,
        declineError,
        logout
      };
    }
  };
  </script>

  <style scoped>
    .detail-item {
      margin-bottom: 15px;
    }

    .detail-label {
      display: block;
      font-weight: 600;
      color: #6c757d;
      font-size: 0.9rem;
    }

    .detail-value {
      font-size: 1.1rem;
      color: var(--dark-color);
    }

    .status-badge {
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 20px;
      font-size: 0.9rem;
      font-weight: 600;
    }

    .status-pending {
      background-color: rgba(255, 193, 7, 0.1);
      color: #ffc107;
    }
  </style>