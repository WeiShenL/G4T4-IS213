import json
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
import os
from dotenv import load_dotenv
from datetime import datetime

import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error("Unhandled Exception: %s", str(e), exc_info=True)
    return jsonify({"error": "An internal server error occurred"}), 500

# RabbitMQ configuration
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_EXCHANGE = "notification_topic"
RABBITMQ_EXCHANGE_TYPE = "topic"

# Service URLs
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://user-service:5000")
RESERVATION_SERVICE_URL = os.environ.get("RESERVATION_SERVICE_URL", "http://reservation-service:5000")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:5000")
WAITLIST_SERVICE_URL = os.environ.get("WAITLIST_SERVICE_URL", "http://waitlist-service:5000")


allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": allowed_origins}})

@app.route("/api/reallocate/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "reallocate-reservation-service",
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

@app.route('/api/reallocate', methods=['POST'])
def reallocate_reservation():
    try:
        data = request.get_json()
        reservation_id = data.get("reservation_id")
        restaurant_id= data.get("restaurant_id")

        if not reservation_id:
            return jsonify({"error": "Missing reservation_id"}), 400

        print(f"Starting reallocation process for reservation ID: {reservation_id}")

        # Call Waitlist service to get the next user in the waitlist
        # NOTE: This now marks the entry as 'processing' - we must confirm or release it
        waitlist_id = None
        try:
            print("Calling Waitlist Service to get next user...")
            waitlist_response = requests.get(f"{WAITLIST_SERVICE_URL}/api/waitlist/Get_nextUser?restaurant_id={restaurant_id}")
            waitlist_response.raise_for_status()
            waitlist_data = waitlist_response.json()
            user_id = waitlist_data.get("user_id")
            waitlist_id = waitlist_data.get("Id")  # Store waitlist_id for confirm/release

            if not user_id or user_id == "0":
                try:
                    delete_response = requests.delete(f"{RESERVATION_SERVICE_URL}/api/reservations/delete/{reservation_id}")
                    delete_response.raise_for_status()
                    print(f"Reservation {reservation_id} successfully deleted.")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to delete reservation {reservation_id}: {str(e)}")
                    return jsonify({"error": f"Failed to delete reservation: {str(e)}"}), 500

                return jsonify({"message": "No users in waitlist. Reservation deleted."}), 200

            print(f"Next user from waitlist: {user_id} (waitlist_id: {waitlist_id})")
        except requests.exceptions.RequestException as e:
            print(f"Error calling Waitlist Service: {str(e)}")
            return jsonify({"error": f"Failed to get waitlist user: {str(e)}"}), 500

        # Helper function to release waitlist entry on failure
        def release_waitlist_on_error():
            if waitlist_id and waitlist_id != 0:
                try:
                    print(f"Releasing waitlist entry {waitlist_id} back to waiting...")
                    requests.patch(f"{WAITLIST_SERVICE_URL}/api/waitlist/release/{waitlist_id}")
                except Exception as release_error:
                    print(f"Warning: Failed to release waitlist entry: {release_error}")

        # Get user details from user service by submitting user_id
        try:
            print(f"Getting user details for user ID: {user_id}")
            user_response = requests.get(f"{USER_SERVICE_URL}/api/user/{user_id}")
            user_response.raise_for_status()
            user_data = user_response.json()

            if user_data.get("code") != 200:
                print(f"Error getting user data: {user_data}")
                release_waitlist_on_error()
                return jsonify({"error": "Failed to get user details"}), 500

            user_details = user_data.get("data", {})
            user_name = user_details.get("customer_name", "Customer")
            user_phone = user_details.get("phone_number", "")

            print(f"Retrieved user details: {user_name}, {user_phone}")

            if not user_name:
                print("Incomplete user details: missing user_name")
                release_waitlist_on_error()
                return jsonify({"error": "Incomplete user details"}), 500
        except requests.exceptions.RequestException as e:
            print(f"Error calling User API: {str(e)}")
            release_waitlist_on_error()
            return jsonify({"error": f"Failed to get user details: {str(e)}"}), 500

        # Update/assign the reservation table with the new user ID
        try:
            print(f"Updating reservation {reservation_id} with new user ID: {user_id}")
            
            # Get the most recent order for this user
            try:
                print(f"Getting orders for user ID: {user_id}")
                orders_response = requests.get(f"{ORDER_SERVICE_URL}/api/orders/user/{user_id}")
                orders_response.raise_for_status()
                orders_data = orders_response.json()
                
                if orders_data.get("code") != 200:
                    print(f"Error getting orders data: {orders_data}")
                    return jsonify({"error": "Failed to get orders details"}), 500
                
                # Get the most recent order (assumed to be first in the list)
                orders = orders_data.get("data", {}).get("orders", [])
                payment_id = None
                order_id = None
                price = 0  # Default to 0 instead of None to avoid NULL in database
                if not orders:
                    print(f"No orders found for user {user_id}, using default price of 0")
                else:
                    # or logic to deduct created_at with current date to retrieve the most recent order
                    most_recent_order = orders[0]  # API returns orders ordered by created_at desc
                    order_id = most_recent_order.get("order_id")
                    payment_id = most_recent_order.get("payment_id")
                    price = most_recent_order.get("order_price", 0) or 0  # Ensure price is never None
                    print(f"Found order ID: {order_id}, payment ID: {payment_id}, and price: {price} for user {user_id}")
            except requests.exceptions.RequestException as e:
                print(f"Error calling Orders API: {str(e)}")
                order_id = None
                payment_id = None
                price = 0  # Default to 0 instead of None
            
            reservation_update_data = {
                "user_id": user_id,
                "status": "Pending",
            }
            
            # Include order_id and payment_id and price in the update if found
            if order_id:
                reservation_update_data["order_id"] = order_id
            if payment_id:
                reservation_update_data["payment_id"] = payment_id
            # Always include price (defaulted to 0 if no orders found)
            reservation_update_data["price"] = price
            
            reservation_response = requests.patch(
                f"{RESERVATION_SERVICE_URL}/api/reservations/reallocate/{reservation_id}", 
                json=reservation_update_data
            )
            reservation_response.raise_for_status()
            reservation_data = reservation_response.json()
            
            print(f"Reservation update response: {reservation_data}")
            
            table_no = reservation_data.get("table_no")
            if not table_no:
                print("Table number missing in reservation response")
                release_waitlist_on_error()
                return jsonify({"error": "Table number missing in reservation response"}), 500
        except requests.exceptions.RequestException as e:
            print(f"Error updating reservation: {str(e)}")
            release_waitlist_on_error()
            return jsonify({"error": f"Failed to update reservation: {str(e)}"}), 500

        # Queue notification message to RabbitMQ
        try:
            print(f"Sending reallocation notice to user: {user_name}")
            notification_data = {
                "user_id": user_id,
                "user_name": user_name,
                "user_phone": user_phone,
                "table_no": table_no,
                "message_type": "reallocation.notice"
            }

            publish_to_rabbitmq("reallocation.notice", notification_data)

            # SUCCESS: Confirm the waitlist entry removal (permanently delete)
            if waitlist_id and waitlist_id != 0:
                try:
                    print(f"Confirming waitlist entry {waitlist_id} removal...")
                    requests.delete(f"{WAITLIST_SERVICE_URL}/api/waitlist/confirm/{waitlist_id}")
                except Exception as confirm_error:
                    print(f"Warning: Failed to confirm waitlist removal: {confirm_error}")

            return jsonify({
                "message": "Reallocation successful",
                "user_id": user_id,
                "reservation_id": reservation_id,
                "table_no": table_no
            }), 200

        except Exception as e:
            app.logger.error("Error during notification in reallocation: %s", str(e), exc_info=True)
            release_waitlist_on_error()
            return jsonify({"code": 500, "error": "An internal server error occurred"}), 500

    except Exception as e:
        app.logger.error("Error during reallocation: %s", str(e), exc_info=True)
        return jsonify({"code": 500, "error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5009))
    print(f"Starting reallocate_reservation service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)