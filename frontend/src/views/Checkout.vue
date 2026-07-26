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
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item" href="#" @click.prevent="logout"><i class="fas fa-sign-out-alt"></i> Logout</a></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Checkout Content -->
    <div class="dashboard-container">
      <div class="container">
        <!-- Page Title -->
        <div class="row mb-4">
          <div class="col-12">
            <div class="welcome-card">
              <h2 v-if="orderType === 'delivery'">Checkout & Delivery</h2>
              <h2 v-else>Checkout & Table Reservation</h2>
              <p v-if="orderType === 'delivery'">Complete your order for delivery</p>
              <p v-else>Complete your reservation and pre-order</p>
            </div>
          </div>
        </div>
        
        <!-- Loading State -->
        <div v-if="isLoading" class="loading-container">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p>Loading checkout details...</p>
        </div>
        
        <!-- Error Message -->
        <div v-if="errorMessage" class="alert alert-danger" role="alert">
          {{ errorMessage }}
        </div>
        
        <!-- Order FOR DELIVERY Placed Success Message -->
        <div v-if="orderPlaced" class="alert alert-success" role="alert">
          <h4 v-if="orderType === 'delivery'" class="alert-heading">Delivery Order Placed Successfully!</h4>
          <h4 v-else class="alert-heading">Reservation & Pre-Order Placed Successfully!</h4>
          <p v-if="orderType === 'delivery'">Your food order has been placed and will be delivered to your address. Thank you!</p>
          <p v-else>Your table has been reserved and your food pre-order has been placed. Thank you!</p>
          
          <!-- Resend Email Notification Banner -->
          <div class="alert alert-info border-0 shadow-sm mt-3 bg-light text-dark">
            <div class="d-flex align-items-center mb-1">
              <i class="fas fa-paper-plane text-primary me-2 fs-5"></i>
              <strong v-if="orderType === 'delivery'">Delivery Order Confirmed Email Dispatched!</strong>
              <strong v-else>Reservation Confirmed Email Dispatched!</strong>
            </div>
            <small class="text-muted d-block">
              An automated confirmation email has been dispatched via Resend API. 
              <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to the developer's testing inbox).</em>
            </small>
          </div>
          <hr>
          <p class="mb-0">Payment ID: {{ paymentId }}</p>
          <div class="mt-3">
            <button v-if="orderType === 'delivery'" @click="goToDeliveryOrdersPage" class="btn btn-primary">
              <i class="fas fa-truck me-2"></i> View My Delivery Orders
            </button>
            <button v-else @click="goToReservations" class="btn btn-primary">
              <i class="fas fa-calendar-check me-2"></i> View My Reservations
            </button>
          </div>
        </div>
        
        <!-- Waitlist Message (if capacity full)--> 
        <div v-if="waitlisted" class="alert alert-warning" role="alert">
          <h4 class="alert-heading">Added to Waitlist!</h4>
          <p>The restaurant is currently at full capacity. We've added you to the waitlist and will notify you when a table becomes available.</p>
          <p>Your order has been processed as "dine-in(pending)" and will be confirmed once a table is available.</p>

          <!-- Resend Email Notification Banner -->
          <div class="alert alert-info border-0 shadow-sm mt-3 bg-light text-dark">
            <div class="d-flex align-items-center mb-1">
              <i class="fas fa-paper-plane text-warning me-2 fs-5"></i>
              <strong>Waitlist Notification Email Dispatched!</strong>
            </div>
            <small class="text-muted d-block">
              A waitlist notification email has been dispatched via Resend API. 
              <em>(Portfolio Note: On the free API sandbox, live email deliveries are routed to the developer's testing inbox).</em>
            </small>
          </div>
          <hr>
          <p class="mb-0">Payment ID: {{ paymentId }}</p>
          <div class="mt-3">
            <button @click="goToReservations" class="btn btn-primary">
              <i class="fas fa-calendar-check me-2"></i> View My Reservations
            </button>
          </div>
        </div>
        
        <!-- Checkout Content -->
        <div v-if="!isLoading && !orderPlaced && !waitlisted && orderInfo" class="row">
          <!-- Order Summary -->
          <div class="col-md-5">
            <div class="card mb-4">
              <div class="card-header">
                <h3 class="mb-0">Order Summary</h3>
              </div>
              <div class="card-body">
                <div class="restaurant-name">
                  <h4>{{ orderInfo.restaurantName }}</h4>
                </div>
                <div class="order-item">
                  <div class="d-flex justify-content-between">
                    <div>
                      <h5>{{ orderInfo.item.name }}</h5>
                      <div class="order-quantity">Quantity: {{ orderInfo.item.quantity }}</div>
                    </div>
                    <div class="order-price">${{ orderInfo.item.price.toFixed(2) }}</div>
                  </div>
                </div>
                <hr>
                <div class="order-subtotal d-flex justify-content-between">
                  <span>Subtotal</span>
                  <span>${{ (orderInfo.item.price * orderInfo.item.quantity).toFixed(2) }}</span>
                </div>
                <div class="order-tax d-flex justify-content-between">
                  <span>Tax (8%)</span>
                  <span>${{ calculateTax().toFixed(2) }}</span>
                </div>
                <div class="order-total d-flex justify-content-between mt-3">
                  <h5>Total</h5>
                  <h5>${{ calculateTotal().toFixed(2) }}</h5>
                </div>
                <div v-if="paymentError" class="alert alert-danger mb-3">
                  {{ paymentError }}
                </div>
                
                <div class="stripe-info alert alert-info mb-3">
                  <i class="fas fa-info-circle me-2"></i>
                  When you click "Proceed to Payment", you'll be redirected to Stripe's secure checkout page to complete your payment and confirm your reservation.
                </div>
                
                <button 
                  type="button" 
                  class="btn btn-primary w-100" 
                  @click="proceedToStripeCheckout" 
                  :disabled="isSubmitting || (orderType === 'dine_in' && (!partySize || !reservationDateTime))"
                >
                  <span v-if="isSubmitting">
                    <i class="fas fa-spinner fa-spin"></i> Processing...
                  </span>
                  <span v-else>
                    <i class="fas fa-credit-card me-2"></i> Proceed to Payment - ${{ calculateTotal().toFixed(2) }}
                  </span>
                </button>
                
                <div class="mt-3 text-center">
                  <small class="text-muted">
                    <i class="fas fa-lock me-1"></i> Secure payment powered by Stripe
                  </small>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Reservation Info for dine-in -->
          <div class="col-md-7" v-if="orderType === 'dine_in'">
            <div class="card">
              <div class="card-header">
                <h3 class="mb-0">Reservation Information</h3>
              </div>
              <div class="card-body">
                <div class="mb-3">
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
                  <small class="text-muted">Please specify how many people will be dining</small>
                </div>
                
                <div class="mb-3">
                  <label for="preferredTable" class="form-label">Preferred Table Number (Optional)</label>
                  <input 
                    type="number" 
                    class="form-control" 
                    id="preferredTable" 
                    v-model="preferredTable" 
                    min="1"
                    required
                  >
                  <small class="text-muted">Leave empty for automatic assignment</small>
                </div>
                
                <div class="mb-3">
                  <label for="reservationDateTime" class="form-label">Reservation Date & Time</label>
                  <input 
                    type="datetime-local" 
                    class="form-control" 
                    id="reservationDateTime" 
                    v-model="reservationDateTime" 
                    required
                  >
                </div>
                
                <div class="mb-3">
                  <label for="specialRequests" class="form-label">Special Requests (Optional)</label>
                  <textarea 
                    class="form-control" 
                    id="specialRequests" 
                    v-model="specialRequests" 
                    rows="2" 
                    placeholder="E.g., Birthday celebration, allergies, etc."
                  ></textarea>
                </div>
              </div>
            </div>
          </div>

          <!-- Delivery Info when order type is delivery -->
          <div class="col-md-7" v-if="orderType === 'delivery'">
            <div class="card">
              <div class="card-header">
                <h3 class="mb-0">Delivery Information</h3>
              </div>
              <div class="card-body">
                <div class="mb-3">
                  <label class="form-label">Delivery Address</label>
                  <div class="delivery-address-display p-3 bg-light rounded">
                    <div><strong>Name:</strong> {{ user?.customerName }}</div>
                    <div><strong>Address:</strong> {{ user?.streetAddress }}</div>
                    <div><strong>Postal Code:</strong> {{ user?.postalCode }}</div>
                    <div><strong>Phone:</strong> {{ user?.phoneNumber }}</div>
                  </div>
                </div>
                
                <div class="mb-3">
                  <label for="deliveryInstructions" class="form-label">Delivery Instructions (Optional)</label>
                  <textarea 
                    class="form-control" 
                    id="deliveryInstructions" 
                    v-model="specialRequests" 
                    rows="2" 
                    placeholder="E.g., Leave at door, call on arrival, etc."
                  ></textarea>
                </div>

                <div class="mb-3">
                  <label for="expectedDeliveryTime" class="form-label">Expected Delivery Time</label>
                  <div class="p-3 bg-light rounded">
                    <p class="mb-0"><i class="fas fa-clock me-2"></i> Approximately 30-45 minutes after order confirmation</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- No Order Info -->
        <div v-if="!isLoading && !orderInfo && !orderPlaced && !waitlisted" class="empty-state">
          <i class="fas fa-shopping-cart"></i>
          <p>No order information found.</p>
          <small>Please select items from a restaurant menu first.</small>
          <div class="mt-3">
            <router-link to="/restaurants" class="btn btn-primary">
              Browse Restaurants
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { getCurrentUser, signOut, supabaseClient } from '@/services/supabase';
import { initStripe, createCheckoutSession, verifyPayment } from '@/services/stripeService';

const API_GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL || 'http://localhost:8000';
const USER_PATH = '/api/user';
const CREATE_BOOKING_PATH = '/api/create';

export default {
  data() {
    return {
      orderType: localStorage.getItem('orderType') };
    },
  name: 'Checkout',
  setup() {
    const router = useRouter();
    const route = useRoute();
    
    const user = ref(null);
    const orderInfo = ref(null);
    const isLoading = ref(true);
    const errorMessage = ref('');
    const paymentError = ref('');
    const isSubmitting = ref(false);
    const orderPlaced = ref(false);
    const waitlisted = ref(false);
    const paymentId = ref('');
    
    // Reservation fields
    const partySize = ref(2); // Default to 2 people
    const preferredTable = ref('');
    const reservationDateTime = ref('');
    const specialRequests = ref('');
    
    // Get restaurant ID from route params
    const restaurantId = parseInt(route.params.id);
    
    // Check if this is a return from Stripe Checkout
    const isReturnFromStripe = computed(() => {
      return route.query.success === 'true' && route.query.session_id;
    });

    const goToReservations = () => {
      router.push('/reservations');
    };
    
    const goToDeliveryOrdersPage = () => {
      router.push('/delivery-orders');
    };
    
    // Set default reservation time to 1 hour from now
    const setDefaultReservationTime = () => {
      const now = new Date();
      now.setHours(now.getHours() + 1);
      now.setMinutes(0); // Round to the nearest hour
      
      // Format for datetime-local input
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const day = String(now.getDate()).padStart(2, '0');
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      
      reservationDateTime.value = `${year}-${month}-${day}T${hours}:${minutes}`;
    };
    
    // Load data when component mounts
    onMounted(async () => {
      try {
        // Make sure we have a valid restaurant ID
        if (!restaurantId || isNaN(restaurantId)) {
          throw new Error('Invalid restaurant ID');
        }
        
        // Initialize Stripe
        await initStripe();
        
        // Load user data
        await loadUserData();

        // only need know address if its delivery type
        const storedOrderType = localStorage.getItem('orderType');
        if (storedOrderType === 'delivery') {
          await loadDeliveryAddressDetails();
        }
        
        // Set default reservation time
        setDefaultReservationTime();
        
        // If returning from Stripe, process the payment
        if (isReturnFromStripe.value) {
          await handleStripeReturn();
        } else {
          // Get order info from localStorage
          const storedOrderInfo = localStorage.getItem('orderInfo');
          if (storedOrderInfo) {
            orderInfo.value = JSON.parse(storedOrderInfo);
            
            // Validate that stored order info matches current restaurant
            if (orderInfo.value.restaurantId !== restaurantId) {
              throw new Error('Order information does not match current restaurant');
            }
          }
        }
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
        
        // Set user data
        user.value = {
          id: currentUser.id,
          customerName: currentUser.user_metadata?.name || 'Customer'
        };
      } catch (error) {
        console.error('Error loading user data:', error);
        throw error;
      }
    };

    // Load delivery address details, based on user id alr have
    const loadDeliveryAddressDetails = async () => {
      const storedOrderType = localStorage.getItem('orderType');
      if (storedOrderType === 'delivery' && user.value && user.value.id) {
        try {
          // Call the user msc to get address details
          const response = await fetch(`${API_GATEWAY_URL}${USER_PATH}/${user.value.id}`);
          const userData = await response.json();
          
          if (userData.code === 200 && userData.data) {
            // Update user with address details
            user.value = {
              ...user.value,
              streetAddress: userData.data.street_address,
              postalCode: userData.data.postal_code,
              phoneNumber: userData.data.phone_number
            };
          }
        } catch (error) {
          console.error('Error loading delivery address:', error);
        }
      }
    };
    
    // Calculate tax
    const calculateTax = () => {
      if (!orderInfo.value) return 0;
      return orderInfo.value.item.total * 0.08; // 8% tax
    };
    
    // Calculate total
    const calculateTotal = () => {
      if (!orderInfo.value) return 0;
      return orderInfo.value.item.total + calculateTax();
    };
    
    // Process payment with Stripe Checkout
    const proceedToStripeCheckout = async () => {
      try {
        if (!orderInfo.value || !user.value) {
          throw new Error('Missing order or user information');
        }
        
        // Validate reservation details
        if (!partySize.value) {
          paymentError.value = 'Please specify the number of people for your reservation';
          return;
        }
        
        if (!reservationDateTime.value) {
          paymentError.value = 'Please select a date and time for your reservation';
          return;
        }
        
        isSubmitting.value = true;
        paymentError.value = '';
        
        // Store reservation info in localStorage for after Stripe return
        localStorage.setItem('reservation_party_size', partySize.value);
        localStorage.setItem('reservation_table_no', preferredTable.value || '');
        localStorage.setItem('reservation_date_time', reservationDateTime.value);
        localStorage.setItem('reservation_special_requests', specialRequests.value || '');
        
        // Save the total amount for verification later
        localStorage.setItem('stripe_amount', calculateTotal());
        
        // Prepare order details for Stripe
        const orderDetails = {
          restaurantId: orderInfo.value.restaurantId,
          restaurantName: orderInfo.value.restaurantName,
          itemName: orderInfo.value.item.name,
          quantity: orderInfo.value.item.quantity,
          amount: calculateTotal() * 100, // Stripe uses cents
          currency: 'usd',
          order_type: localStorage.getItem('orderType')
        };
        
        // Set up success and cancel URLs
        const currentUrl = window.location.origin;
        const successUrl = `${currentUrl}/checkout/${orderInfo.value.restaurantId}?success=true&session_id={CHECKOUT_SESSION_ID}`;
        const cancelUrl = `${currentUrl}/checkout/${orderInfo.value.restaurantId}?canceled=true`;
        
        console.log('Creating Stripe checkout session...');
        
        // Create a checkout session
        const { sessionId, url } = await createCheckoutSession(
          orderDetails,
          user.value.id,
          successUrl,
          cancelUrl
        );
        
        console.log('Redirecting to Stripe checkout...');
        
        // Redirect to Stripe Checkout
        const { error } = await initStripe().then(stripe => 
          stripe.redirectToCheckout({ sessionId })
        );
        
        if (error) {
          throw new Error(error.message);
        }
      } catch (error) {
        console.error('Error processing payment:', error);
        paymentError.value = error.message || 'Payment initialization failed. Please try again.';
        isSubmitting.value = false;
      }
    };
    
    // Handle return from Stripe
    const handleStripeReturn = async () => {
      try {
        isLoading.value = true;
        
        // sess id
        const sessionId = route.query.session_id;

        // throw exception
        if (!sessionId){
          throw new Error("Invalid session information")
        }

        // chk payment status
        const verificationResult = await verifyPayment(sessionId);
        if (!verificationResult.paymentIntent || verificationResult.paymentIntent.status !== 'succeeded') {
          throw new Error('Payment verification failed');
        }

        // Get payment intent ID 
        const stripePaymentIntentId = verificationResult.paymentIntent.id;
        
        if (!stripePaymentIntentId) {
          throw new Error('Invalid payment information');
        }
        
        // Restore order info from localStorage
        const storedOrderInfo = localStorage.getItem('orderInfo');
        if (!storedOrderInfo) {
          throw new Error('Order information not found');
        }
        
        orderInfo.value = JSON.parse(storedOrderInfo);
        
        // Get reservation info from localStorage
        const storedPartySize = localStorage.getItem('reservation_party_size');
        const storedTableNo = localStorage.getItem('reservation_table_no');
        const storedDateTime = localStorage.getItem('reservation_date_time');
        const storedOrderType = localStorage.getItem('orderType');

        if (!storedPartySize || !storedDateTime) {
          throw new Error('Reservation information not found');
        }
        
        // Create booking (order + reservation) via create_booking microservice
        console.log('Creating booking via microservice');
        const bookingData = {
          restaurant_id: orderInfo.value.restaurantId,
          user_id: user.value.id,
          table_no: storedTableNo || null, 
          status: 'Booked',
          count: parseInt(storedPartySize),
          order_price: calculateTotal(),
          time: new Date(storedDateTime).toISOString(),
          payment_id: stripePaymentIntentId,
          item_name: orderInfo.value.item.name,
          quantity: orderInfo.value.item.quantity,
          order_type: storedOrderType
        };

        console.log('Creating booking with data:', bookingData);
        const bookingResponse = await fetch(`${API_GATEWAY_URL}${CREATE_BOOKING_PATH}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(bookingData)
        });

        if (!bookingResponse.ok) {
          const errorData = await bookingResponse.json();
          throw new Error(`Failed to create booking: ${errorData.error || bookingResponse.statusText}`);
        }

        const bookingResult = await bookingResponse.json();
        
        if (bookingResult.status === "booked") {
          // Clear stored data from localStorage
          localStorage.removeItem('orderInfo');
          localStorage.removeItem('reservation_party_size');
          localStorage.removeItem('reservation_table_no');
          localStorage.removeItem('reservation_date_time');
          localStorage.removeItem('reservation_special_requests');
          localStorage.removeItem('stripe_payment_intent_id');
          localStorage.removeItem('stripe_amount');
          localStorage.removeItem('orderType');

          // Set payment ID for display
          paymentId.value = stripePaymentIntentId;
          
          // Show success message
          orderPlaced.value = true;
          // waitlist scenario hereeee
        } else if (bookingResult.status === "waitlisted") {
          // Clear stored data from localStorage
          localStorage.removeItem('orderInfo');
          localStorage.removeItem('reservation_party_size');
          localStorage.removeItem('reservation_table_no');
          localStorage.removeItem('reservation_date_time');
          localStorage.removeItem('reservation_special_requests');
          localStorage.removeItem('stripe_payment_intent_id');
          localStorage.removeItem('stripe_amount');
          localStorage.removeItem('orderType');

          // Set payment ID for display
          paymentId.value = stripePaymentIntentId;
          
          // Show waitlist message by setting a new state
          waitlisted.value = true;
        }
      } catch (error) {
        console.error('Error handling Stripe return:', error);
        errorMessage.value = error.message || 'Failed to process your payment. Please contact support.';
      } finally {
        isLoading.value = false;
      }
    };
    
    // Logout function
    const logout = async () => {
      try {
        isLoading.value = true;
        await signOut();
        router.push('/');
      } catch (error) {
        console.error('Logout error:', error);
        errorMessage.value = 'Failed to log out. Please try again.';
      } finally {
        isLoading.value = false;
      }
    };
    
    // Simple method to toggle dropdown manually
    const toggleDropdown = (event) => {
      const dropdownMenu = event.target.closest('.dropdown').querySelector('.dropdown-menu');
      dropdownMenu.classList.toggle('show');
    };
    
    return {
      user,
      orderInfo,
      isLoading,
      errorMessage,
      paymentError,
      isSubmitting,
      orderPlaced,
      waitlisted,
      paymentId,
      partySize,
      preferredTable,
      reservationDateTime,
      specialRequests,
      calculateTax,
      calculateTotal,
      proceedToStripeCheckout,
      goToReservations,
      goToDeliveryOrdersPage,
      logout,
      toggleDropdown
    };
  }
};
</script>

<style scoped>
.restaurant-name {
  margin-bottom: 20px;
}

.order-item {
  margin-bottom: 20px;
}

.order-quantity {
  color: #6c757d;
  font-size: 0.9rem;
}

.order-price {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--primary-color);
}

.order-subtotal, .order-tax {
  margin-bottom: 5px;
  color: #6c757d;
}

.order-total {
  font-size: 1.2rem;
  color: var(--dark-color);
  border-top: 1px solid #eee;
  padding-top: 10px;
}

.stripe-info {
  background-color: rgba(0, 123, 255, 0.05);
  border-color: rgba(0, 123, 255, 0.1);
  color: #0056b3;
}
</style>