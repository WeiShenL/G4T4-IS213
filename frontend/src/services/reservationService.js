// import Supabase client 
import { supabaseClient } from './supabase';

// base URLs for the API
// const RESERVATION_API_URL = 'http://localhost:5002/api';
// const CANCEL_BOOKING_URL = 'http://localhost:5008/cancel';
// // const REALLOCATION_URL = 'http://localhost:5002/reservation/reallocate_confirm_booking';
// const ACCEPT_REALLOCATION_URL = 'http://localhost:5010/accept-reallocation';


// Get API gateway URL from environment variables
const API_GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL || 'http://localhost:8000';

// API paths through Kong
const RESERVATION_PATH = '/api/reservations';
const ORDER_PATH = '/api/orders';
const ACCEPT_REALLOCATION_PATH = '/api/accept-reallocation';

// get auth headers
const getAuthHeaders = async () => {
  const { data } = await supabaseClient.auth.getSession();
  const token = data.session?.access_token;
  
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};

// Get user reservations
export const getUserReservations = async (userId) => {
  try {
    if (!userId) {
      throw new Error('User ID is required');
    }
    
    const headers = await getAuthHeaders();
    
    // Pass userId as a string
    const response = await fetch(`${API_GATEWAY_URL}${RESERVATION_PATH}/user/${userId}`, {
      headers
    });
    
    const data = await response.json();
    
    if (data.code === 200) {
      return data.data.reservations;
    } else if (data.code === 404) {
      return [];
    } else {
      throw new Error(data.message || 'Failed to fetch user reservations');
    }
  } catch (error) {
    console.error('Error fetching user reservations:', error);
    throw error;
  }
};

// Get user waitlist entries from waitlist microservice
export const getUserWaitlist = async (userId) => {
  try {
    if (!userId) return [];
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_GATEWAY_URL}/api/waitlist/user/${userId}`, { headers });
    const data = await response.json();
    if (data.code === 200) {
      return data.data.waitlist || [];
    }
    return [];
  } catch (error) {
    console.error('Error fetching user waitlist:', error);
    return [];
  }
};

// Check for pending reservations (status = 'Pending')
export const checkPendingReservations = async (userId) => {
  try {
    if (!userId) {
      throw new Error('User ID is required');
    }
    
    // Get all user reservations
    const reservations = await getUserReservations(userId);
    
    // Filter for pending ones
    return reservations.filter(res => res.status === 'Pending');
  } catch (error) {
    console.error('Error checking pending reservations:', error);
    throw error;
  }
};

// Accept a reallocation
export const acceptReallocation = async (acceptData) => {
  try {
    const reservationId = acceptData.reservation_id;
    if (!reservationId) {
      throw new Error('Reservation ID is required');
    }
    
    const headers = await getAuthHeaders();
    
    console.log(`Accepting reallocation for reservation ID: ${reservationId}`);
    
    // Make a request to the order service to retrieve order details by user_id
    const orderResponse = await fetch(`${API_GATEWAY_URL}${ORDER_PATH}/user/${acceptData.user_id}`);
    
    if (!orderResponse.ok) {
      throw new Error('Failed to retrieve order information');
    }
    
    const orderData = await orderResponse.json();
    let orderId = null;
    let paymentId = null;
    let price = 0;
    
    // Extract order details if available
    if (orderData.code === 200 && orderData.data && orderData.data.orders && orderData.data.orders.length > 0) {
      // Assuming the first order is the most recent one
      const order = orderData.data.orders[0];
      orderId = order.order_id;
      paymentId = order.payment_id;
      price = order.order_price;
    } else {
      // if no orders found, generate mock data
      console.log('No order found for user, using default values');
      orderId = Math.floor(Math.random() * 1000);
      paymentId = `py_${Date.now()}`;
      price = 0;
    }
    
    // Prepare data for the accept-reallocation endpoint
    const bookingData = {
      reservation_id: reservationId,
      user_id: acceptData.user_id,
      count: acceptData.count,
      payment_id: paymentId,
      order_id: orderId,
      price: price,
      booking_time: acceptData.booking_time
    };
    
    // Send the data to the accept-reallocation endpoint
    const response = await fetch(`${API_GATEWAY_URL}${ACCEPT_REALLOCATION_PATH}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(bookingData)
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to confirm reservation');
    }
    
    const data = await response.json();
    console.log('Booking accepted:', data);
    
    return {
      success: true,
      message: 'Reservation confirmed successfully',
      data: data
    };
    
  } catch (error) {
    console.error('Error accepting reallocation:', error);
    throw error;
  }
};

// Decline/Cancel a reallocation (give to next customer in waitlist)
export const cancelReallocation = async (reservationId) => {
  try {
    if (!reservationId) {
      throw new Error('Reservation ID is required');
    }

    const headers = await getAuthHeaders();

    console.log(`Sending reallocation decline request to: ${API_GATEWAY_URL}${ACCEPT_REALLOCATION_PATH}/decline/${reservationId}`);

    const response = await fetch(`${API_GATEWAY_URL}${ACCEPT_REALLOCATION_PATH}/decline/${reservationId}`, {
      method: 'POST',
      headers
    });

    const data = await response.json();
    console.log('Reallocation decline API response:', data);

    if (!response.ok) {
      throw new Error(data.error || 'Failed to decline reallocated reservation');
    }

    return {
      success: true,
      message: data.message || 'Reallocated reservation declined successfully',
      data: data
    };
  } catch (error) {
    console.error('Error declining reallocated reservation:', error);
    return {
      success: false,
      message: error.message || 'An error occurred during reallocation decline',
      error: error
    };
  }
};