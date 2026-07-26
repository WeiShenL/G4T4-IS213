import json
import time
import requests
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RabbitMQ configuration
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_EXCHANGE = "notification_topic"
RABBITMQ_EXCHANGE_TYPE = "topic"

# Service URLs
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://user-service:5000")
RESTAURANT_SERVICE_URL = os.environ.get("RESTAURANT_SERVICE_URL", "http://restaurant-service:5000")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:5000")
RESERVATION_SERVICE_URL = os.environ.get("RESERVATION_SERVICE_URL", "http://reservation-service:5000")
WAITLIST_SERVICE_URL = os.environ.get("WAITLIST_SERVICE_URL", "http://waitlist-service:5000")

import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error("Unhandled Exception: %s", str(e), exc_info=True)
    return jsonify({"error": "An internal server error occurred"}), 500
# Allow CORS for allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": allowed_origins}})

@app.route("/api/create/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "create-booking-service",
        "timestamp": datetime.now().isoformat()
    }), 200

# Publish message to RabbitMQ
def publish_to_rabbitmq(routing_key, message):
    """Publish a message to RabbitMQ"""
    try:
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT
            )
        )
        channel = connection.channel()
        
        # Ensure exchange exists
        channel.exchange_declare(
            exchange=RABBITMQ_EXCHANGE,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
            durable=True
        )
        
        # Publish message
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(message)
        )
        
        # Close connection
        connection.close()
        print(f"Published message to {routing_key}: {json.dumps(message)}")
        return True
    except Exception as e:
        print(f"Error publishing to RabbitMQ: {e}")
        return False

# order create first, once success 200 then call reservation
@app.route('/api/create', methods=['POST'])
def create_booking():
    try:
        # Get request data
        data = request.json
        order_type = data.get('order_type', 'dine_in')
        
        # Validate required fields for the combined order and reservation
        required_fields = [
            'restaurant_id', 'user_id', 'payment_id',
            'item_name', 'quantity', 'order_price'
        ]
        
        if order_type == 'dine_in':
            # Additional fields required for dine-in orders
            required_fields.extend(['count', 'time'])
        
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create the order with the appropriate order_type (dine_in or delivery)
        order_data = {
            "user_id": data['user_id'],
            "restaurant_id": data['restaurant_id'],
            "item_name": data['item_name'],
            "quantity": data['quantity'],
            "order_price": data['order_price'],
            "payment_id": data['payment_id'],
            "order_type": "dine_in(pending)" if order_type == 'dine_in' else "delivery"
        }
        
        # Call order service to create the order
        print(f"Creating order with data: {order_data}")
        order_response = requests.post(
            f"{ORDER_SERVICE_URL}/api/orders",
            json=order_data
        )
        
        if not order_response.ok:
            error_data = order_response.json()
            return jsonify({
                "error": f"Failed to create order: {error_data.get('message', order_response.status_code)}"
            }), order_response.status_code
        
        # Get the created order details
        order_data = order_response.json()
        print(f"Order created: {order_data}")
        
        # Get the order ID from the response
        order_id = order_data.get("data", {}).get("order_id")
        if not order_id:
            return jsonify({"error": "Order ID not found in response"}), 500
        
        # Handle delivery order vs. dine-in order
        if order_type == 'delivery':
            # For delivery orders, we're done - no reservation needed
            # Queue a delivery confirmation message to RabbitMQ
            try:
                # Get user details for notifications
                user_id = data.get("user_id")
                try:
                    user_response = requests.get(f"{USER_SERVICE_URL}/api/user/{user_id}")
                    user_response.raise_for_status()
                    user_data = user_response.json()
                    
                    # Extract the user details we need
                    user_name = user_data.get("data", {}).get("customer_name", "Customer")
                    user_phone = user_data.get("data", {}).get("phone_number", "")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch user details: {str(e)}")
                    user_name = "Customer"
                    user_phone = ""
                    
                # Get restaurant details
                restaurant_id = data['restaurant_id']
                try:
                    restaurant_response = requests.get(f"{RESTAURANT_SERVICE_URL}/api/restaurants/{restaurant_id}")
                    restaurant_response.raise_for_status()
                    restaurant_data = restaurant_response.json()
                    
                    # Extract restaurant name
                    restaurant_name = restaurant_data.get("data", {}).get("name", f"Restaurant #{restaurant_id}")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to fetch restaurant details: {str(e)}")
                    restaurant_name = f"Restaurant #{restaurant_id}"
                
                notification_data = {
                    "order_id": order_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_phone": user_phone,
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                    "payment_id": data.get("payment_id"),
                    "message_type": "delivery.order.confirmation"
                }
                
                notification_sent = publish_to_rabbitmq("delivery.order.confirmation", notification_data)
                
                status_message = "Delivery order created and confirmation notification sent."
                status_code = 201
                
                if not notification_sent:
                    status_message = "Delivery order created but notification could not be sent (RabbitMQ issue)."
                    status_code = 207  # Partial success
                
                # Return response with appropriate message
                return jsonify({
                    "message": status_message,
                    "status": "booked",
                    "order_id": order_id,
                    "data": {
                        "order": order_data.get("data", {})
                    }
                }), status_code
                
            except Exception as e:
                print(f"Error in notification handling: {str(e)}")
                # Return partial success since the order was created
                return jsonify({
                    "message": "Delivery order created but notification could not be sent.",
                    "status": "booked",
                    "order_id": order_id,
                    "data": {
                        "order": order_data.get("data", {})
                    }
                }), 207
        
        # here, means is a dine-in order alr
        # Get restaurant capacity and current reservations
        restaurant_id = data['restaurant_id']
        print(f"Checking capacity for restaurant {restaurant_id}")
        capacity_response = requests.get(
            f"{RESTAURANT_SERVICE_URL}/api/restaurants/capacity/{restaurant_id}"
        )
        
        if not capacity_response.ok:
            error_data = capacity_response.json()
            return jsonify({
                "error": f"Failed to check restaurant capacity: {error_data.get('message', capacity_response.status_code)}"
            }), capacity_response.status_code
            
        capacity_data = capacity_response.json()
        restaurant_capacity = capacity_data.get("data", {}).get("capacity", 0)
        
        # Count only ACTIVE reservations with status="Booked" (not all orders)
        # This fixes the critical bug where all historical orders were counted
        active_reservations_response = requests.get(
            f"{RESERVATION_SERVICE_URL}/api/reservations/restaurant/{restaurant_id}/active"
        )

        current_reservations = 0
        if active_reservations_response.ok:
            reservations_data = active_reservations_response.json()
            active_reservations = reservations_data.get("data", {}).get("reservations", [])
            current_reservations = len(active_reservations)
        else:
            # Fallback: if endpoint doesn't exist, try to get all reservations and filter
            print(f"Warning: Active reservations endpoint failed, using fallback")
            all_reservations_response = requests.get(
                f"{RESERVATION_SERVICE_URL}/api/reservations/restaurant/{restaurant_id}"
            )
            if all_reservations_response.ok:
                all_data = all_reservations_response.json()
                all_reservations = all_data.get("data", {}).get("reservations", [])
                # Count only reservations with status "Booked"
                current_reservations = sum(1 for r in all_reservations if r.get("status") == "Booked")

        available_slots = max(0, restaurant_capacity - current_reservations)
        
        print(f"Restaurant capacity: {restaurant_capacity}, Current dine-in reservations: {current_reservations}")
        
        # Get user details for notifications
        user_id = data.get("user_id")
        try:
            user_response = requests.get(f"{USER_SERVICE_URL}/api/user/{user_id}")
            user_response.raise_for_status()
            user_data = user_response.json()
            
            # Extract the user details we need
            user_name = user_data.get("data", {}).get("customer_name", "Customer")
            user_phone = user_data.get("data", {}).get("phone_number", "")
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch user details: {str(e)}")
            user_name = "Customer"
            user_phone = ""
            
        # Get restaurant details
        try:
            restaurant_response = requests.get(f"{RESTAURANT_SERVICE_URL}/api/restaurants/{restaurant_id}")
            restaurant_response.raise_for_status()
            restaurant_data = restaurant_response.json()
            
            # Extract restaurant name
            restaurant_name = restaurant_data.get("data", {}).get("name", f"Restaurant #{restaurant_id}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch restaurant details: {str(e)}")
            restaurant_name = f"Restaurant #{restaurant_id}"
            
        # Check if restaurant is at capacity
        if current_reservations >= restaurant_capacity:
            print(f"Restaurant at capacity. Adding user to waitlist.")
            
            # Add user to waitlist via Waitlist Service
            waitlist_data = {
                "user_id": user_id,
                "restaurant_id": restaurant_id
            }

            try:
                waitlist_response = requests.post(
                    f"{WAITLIST_SERVICE_URL}/api/waitlist/addUser",
                    json=waitlist_data
                )
                
                # Queue waitlist notification to RabbitMQ
                notification_data = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_phone": user_phone,
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                    "time": data.get("time"),
                    "count": data.get("count"),
                    "payment_id": data.get("payment_id"),
                    "order_id": order_id,
                    "message_type": "waitlist.notification"
                }
                
                notification_sent = publish_to_rabbitmq("waitlist.notification", notification_data)
                
                if not notification_sent:
                    print("Warning: Could not send waitlist notification (RabbitMQ issue).")
                
                # Return response indicating waitlist status
                return jsonify({
                    "message": "Restaurant is at capacity. You have been added to the waitlist.",
                    "status": "waitlisted",
                    "order_id": order_id,
                    "data": {
                        "order": order_data.get("data", {})
                    }
                }), 200
                
            except Exception as e:
                print(f"Error adding to waitlist: {str(e)}")
                return jsonify({
                    "error": f"Failed to add to waitlist: {str(e)}"
                }), 500
        
        # If we reach here, there's capacity available, create the reservation
        reservation_data = {
            "restaurant_id": data['restaurant_id'],
            "user_id": data['user_id'],
            "table_no": data.get('table_no'),
            "status": data.get('status', 'Booked'),
            "count": data['count'],
            "price": data['order_price'],
            "time": data['time'],
            "order_id": order_id,
            "payment_id": data['payment_id']
        }
        
        # Call reservation service
        print(f"Creating reservation with data: {reservation_data}")
        reservation_response = requests.post(
            f"{RESERVATION_SERVICE_URL}/api/reservations",
            json=reservation_data
        )
        
        if not reservation_response.ok:
            error_data = reservation_response.json()
            # ROLLBACK: Delete the order since reservation failed
            # This prevents orphaned orders (order exists but no reservation)
            try:
                print(f"Rolling back order {order_id} due to reservation failure...")
                rollback_response = requests.delete(f"{ORDER_SERVICE_URL}/api/orders/{order_id}")
                if rollback_response.ok:
                    print(f"Successfully rolled back order {order_id}")
                else:
                    print(f"Warning: Failed to rollback order {order_id}: {rollback_response.text}")
            except Exception as rollback_error:
                print(f"Warning: Exception during order rollback: {rollback_error}")

            return jsonify({
                "error": f"Failed to create reservation: {error_data.get('message', reservation_response.status_code)}"
            }), reservation_response.status_code
        
        # Get the created reservation details
        reservation_data = reservation_response.json()
        print(f"Reservation created: {reservation_data}")
        
        # Update order type to "dine_in"
        order_update_response = requests.patch(
            f"{ORDER_SERVICE_URL}/api/orders/{order_id}/type",
            json={"order_type": "dine_in"}
        )
        
        if not order_update_response.ok:
            print(f"Warning: Failed to update order type: {order_update_response.text}")
        
        # Get the reservation ID from the response
        reservation_id = reservation_data.get("data", {}).get("reservation_id")
        if not reservation_id:
            return jsonify({"error": "Reservation ID not found in response"}), 500
        
        # Once the reservation is created, send a confirmation notification
        notification_data = {
            "reservation_id": reservation_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_phone": user_phone,
            "table_no": reservation_data.get("table_no", ""),
            "booking_time": data.get("time"),
            "restaurant_name": restaurant_name,
            "message_type": "reservation.confirmation"
        }
        
        notification_sent = publish_to_rabbitmq("reservation.confirmation", notification_data)
        
        if not notification_sent:
            print("Warning: Could not send notification (RabbitMQ issue).")
        
        # Return response with appropriate message
        return jsonify({
            "message": "Booking created and confirmation notification sent.",
            "status": "booked",
            "order_id": order_id,
            "reservation_id": reservation_id,
            "data": {
                "order": order_data.get("data", {}),
                "reservation": reservation_data.get("data", {})
            }
        }), 201
    
    except Exception as e:
        app.logger.error("Error in create_booking: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "error": "An internal server error occurred"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5007))
    print("Starting create_booking service...")
    app.run(host='0.0.0.0', port=port, debug=True)