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

# Load environment variables
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
PAYMENT_SERVICE_URL = os.environ.get("PAYMENT_SERVICE_URL", "http://payment-service:5000")
NOTIFICATION_SERVICE_URL = os.environ.get("NOTIFICATION_SERVICE_URL", "http://notification-service:5000")
REALLOCATE_RESERVATION_SERVICE_URL = os.environ.get("REALLOCATE_RESERVATION_SERVICE_URL", "http://reallocate-reservation-service:5000")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": allowed_origins}})

@app.route("/api/cancel/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "cancel-booking-service",
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

@app.route('/api/cancel/<int:reservation_id>', methods=['POST'])
def process_cancellation(reservation_id):
    # STEP 1: Get reservation data FIRST (without cancelling)
    # This allows us to process refund before committing to cancellation
    try:
        reservation_response = requests.get(
            f"{RESERVATION_SERVICE_URL}/api/reservations/{reservation_id}"
        )
        reservation_response.raise_for_status()
        reservation_result = reservation_response.json()

        if reservation_result.get("code") != 200:
            return jsonify({"error": "Reservation not found"}), 404

        reservation_data = reservation_result.get("data", {})
        print(f"Reservation data received: {reservation_data}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to get reservation: {str(e)}")
        return jsonify({"error": f"Failed to get reservation: {str(e)}"}), 500

    # Extract required fields from the reservation
    user_id = reservation_data.get("user_id")
    table_no = reservation_data.get("table_no")
    restaurant_id = reservation_data.get("restaurant_id")
    refund_amount = reservation_data.get("price", 0)
    payment_id = reservation_data.get("payment_id")
    order_id = reservation_data.get("order_id")

    if not user_id:
        return jsonify({"error": "No user associated with this reservation"}), 404

    # Get user details from customer_profiles table
    try:
        user_response = requests.get(f"{USER_SERVICE_URL}/api/user/{user_id}")
        user_response.raise_for_status()
        user_data = user_response.json()
        print(f"User data received: {user_data}")

        user_name = user_data.get("data", {}).get("customer_name", "Customer")
        user_phone = user_data.get("data", {}).get("phone_number", "")

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch user details: {str(e)}")
        return jsonify({"error": f"Failed to fetch user details: {str(e)}"}), 500

    # STEP 2: Process refund BEFORE cancelling reservation
    # This prevents user from losing money if refund fails
    if payment_id:
        try:
            refund_response = requests.post(
                f"{PAYMENT_SERVICE_URL}/api/payment/refund",
                json={"payment_id": payment_id}
            )
            refund_response.raise_for_status()
            refund_data = refund_response.json()
            print(f"Refund processed: {refund_data}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to process refund: {str(e)}")
            # CRITICAL: Do NOT proceed with cancellation if refund fails
            # User would lose their money otherwise
            return jsonify({
                "error": f"Cancellation aborted: Refund failed - {str(e)}",
                "message": "Your reservation is still active. Please try again or contact support."
            }), 500

    # STEP 3: Only cancel reservation AFTER successful refund
    try:
        cancel_response = requests.patch(
            f"{RESERVATION_SERVICE_URL}/api/reservation/cancel/{reservation_id}"
        )
        cancel_response.raise_for_status()
        print(f"Reservation {reservation_id} cancelled successfully")
    except requests.exceptions.RequestException as e:
        print(f"Failed to cancel reservation: {str(e)}")
        # Refund was already processed - this is a partial failure
        # Log for manual reconciliation but don't fail completely
        return jsonify({
            "error": f"Refund processed but cancellation failed: {str(e)}",
            "message": "Your refund was processed. Please contact support to complete cancellation.",
            "refund_processed": True,
            "payment_id": payment_id
        }), 207  # Partial success

    # STEP 4: Delete the order (after both refund and cancellation succeeded)
    if order_id:
        try:
            delete_order_response = requests.delete(
                f"{ORDER_SERVICE_URL}/api/orders/{order_id}"
            )
            if delete_order_response.status_code == 200:
                print(f"Order with ID {order_id} deleted successfully")
            else:
                print(f"Warning: Failed to delete order {order_id}")
        except Exception as e:
            print(f"Warning: Exception deleting order: {e}")
    
    # Queue a notification message to RabbitMQ and trigger reallocation
    try:
        notification_data = {
            "reservation_id": reservation_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_phone": user_phone,
            "table_no": table_no,
            "refund_amount": refund_amount,
            "payment_id": payment_id,
            "message_type": "reservation.cancellation"
        }
        
        publish_to_rabbitmq("reservation.cancellation", notification_data)

        # Trigger reallocation with retry logic (composite orchestration)
        reallocation_data = {"reservation_id": reservation_id, "restaurant_id": restaurant_id}
        reallocation_success = False
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                reallocation_response = requests.post(
                    f"{REALLOCATE_RESERVATION_SERVICE_URL}/api/reallocate",
                    json=reallocation_data,
                    timeout=10
                )
                if reallocation_response.ok:
                    reallocation_success = True
                    print(f"Reallocation successful on attempt {attempt + 1}")
                    break
                else:
                    print(f"Reallocation attempt {attempt + 1} failed: {reallocation_response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Reallocation attempt {attempt + 1} error: {str(e)}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

        return jsonify({
            "message": "Reservation cancelled and notification sent." + (" Reallocation triggered." if reallocation_success else " Reallocation could not be completed."),
            "status": "cancelled",
            "reservation_id": reservation_id,
            "payment_id": payment_id,
            "reallocation_triggered": reallocation_success
        }), 200
    except Exception as e:
        app.logger.error("Error triggering notification or reallocation: %s", str(e), exc_info=True)
        return jsonify({"code": 500, "error": "An internal server error occurred"}), 500

# # calls the existing method
# @app.route('/api/cancel/reallocation/<int:reservation_id>', methods=['POST'])
# def cancel_reallocation(reservation_id):
#     # Simply call the existing cancellation method - it already does everything needed
#     return process_cancellation(reservation_id)



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5008))
    print(f"Starting cancel_booking service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)