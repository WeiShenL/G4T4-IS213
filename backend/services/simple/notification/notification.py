import os
import json
import threading
import pika
import time
import logging
import html
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import resend
from datetime import datetime
from supabase import create_client, Client as SupabaseClient
from werkzeug.exceptions import HTTPException

# Load environment variables
load_dotenv()

# RabbitMQ configuration
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_EXCHANGE = "notification_topic"
RABBITMQ_EXCHANGE_TYPE = "topic"

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.error("Unhandled Exception: %s", str(e), exc_info=True)
    return jsonify({"error": "An internal server error occurred"}), 500

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": allowed_origins, "methods": ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]}})

@app.route("/api/notification/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "notification-service",
        "provider": "resend",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# Supabase configuration
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Resend Email Configuration
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Subject line mappings for events
EVENT_SUBJECTS = {
    "reservation.confirmation": "Your FeastFinder Reservation is Confirmed!",
    "waitlist.notification": "You're on the Waitlist - FeastFinder",
    "reservation.cancellation": "Reservation Cancellation Notice - FeastFinder",
    "reservation.decline": "Table Offer Declined - FeastFinder",
    "reallocation.notice": "Table Available - FeastFinder",
    "reallocation.confirmation": "Reallocation Confirmed - FeastFinder",
    "delivery.order.confirmation": "Order Confirmation - FeastFinder",
    "delivery.order.accepted": "Driver Assigned to Your Order - FeastFinder",
    "delivery.order.pickedup": "Order Picked Up - FeastFinder",
    "delivery.order.delivered": "Order Delivered - FeastFinder"
}

# Message templates for different event types
MESSAGE_TEMPLATES = {
    #US1
    "reservation.confirmation": "Hi there {username}! Your reservation (ID: {reservation_id}) has been confirmed. See you soon!",
    "waitlist.notification": "Hi {username}! The restaurant {restaurant_name} is currently at full capacity. We've added you to the waitlist and will notify you when a table becomes available. Thank you for your patience!",

    #US2
    "reservation.cancellation": "Hi there {username}! Your reservation (ID: {reservation_id}) has been canceled and a refund of ${refund_amount} has been processed. We look forward to seeing you again! Thank you!",
    "reservation.decline": "Hi there {username}! You have declined the table offer for Table {table_no}. A refund of ${refund_amount} has been processed if applicable. Thank you!",
    "reallocation.notice": "Hi there {username}! Table {table_no} is currently open, would you like to book it? If so, please click on this link: http://localhost:5173 to start the booking process!",
    "reallocation.confirmation": "Hi {username}, your reservation (ID: {reservation_id}) for Table {table_no} has been confirmed for {booking_time}. Thank you!",
    
    #US3
    "delivery.order.confirmation": "Hi there {username}! Your order (ID: {order_id}) has been confirmed for delivery. Thank you for ordering with us!",
    "delivery.order.accepted": "Hi there {customer_name}! Your order (ID: {order_id}) has been assigned a driver, {driver_name}. Thank you for ordering with us!",
    "delivery.order.pickedup": "Good news {customer_name}! Your order (ID: {order_id}) has been picked up by your allocated driver. {driver_name} is on the way!",
    "delivery.order.delivered": "Hello {customer_name}! Your order (ID: {order_id}) has been delivered. Thank you for your purchase and we hope to see you soon!"
}

# Sends an email via Resend API
def send_email(to_email, subject, message):
    try:
        if not RESEND_API_KEY:
            logging.warning("RESEND_API_KEY is not set. Email notification logged locally.")
            return {"status": "skipped", "reason": "No RESEND_API_KEY configured"}
            
        escaped_message = html.escape(message)
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #e63946; margin-bottom: 16px;">FeastFinder</h2>
                <p style="font-size: 16px; line-height: 1.5; color: #333;">{escaped_message}</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
                <p style="font-size: 12px; color: #888;">Thank you for using FeastFinder!</p>
            </div>
            """
        }
        
        email_res = resend.Emails.send(params)
        email_id = email_res.get("id") if isinstance(email_res, dict) else getattr(email_res, "id", str(email_res))
        logging.info(f"Email sent successfully to {to_email} (ID: {email_id})")
        return {"status": "success", "email_id": email_id}
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return {"status": "failed", "error": str(e)}

# Save the notification to DB
def save_notification_to_db(message, msg_type, status):
    try:
        notification_data = {
            "message": message,
            "status": status,
            "type": msg_type,
        }
        
        response = supabase.table('notification').insert(notification_data).execute()
        
        if not response.data:
            logging.error("Failed to save notification to Supabase")
        else:
            logging.info(f"Notification saved to Supabase: {response.data[0].get('id')}")
            
    except Exception as e:
        logging.error(f"Error saving notification to Supabase: {e}")

def rabbitmq_callback(ch, method, properties, body):
    try:
        logging.info(f"Received message: {body}")
        data = json.loads(body)
        
        msg_type = data.get("message_type")
        recipient_email = os.getenv("DEFAULT_RECIPIENT_EMAIL") or data.get("user_email") or data.get("customer_email") or data.get("email") or "delivered@resend.dev"
        table_no = data.get("table_no", "N/A")
        username = data.get("user_name", "there")
        reservation_id = data.get("reservation_id", "N/A")
        refund_amount = data.get("refund_amount", "N/A")
        restaurant_name = data.get("restaurant_name", "The restaurant")
        booking_time = data.get("booking_time", "N/A")
        order_id = data.get("order_id", "N/A")

        driver_name = data.get("driver_name", "Driver") 
        customer_name = data.get("customer_name", "Customer") 
        
        # Format booking_time if available
        if booking_time != "N/A" and booking_time:
            try:
                booking_dt = datetime.fromisoformat(booking_time.replace('Z', '+00:00'))
                booking_time = booking_dt.strftime("%A, %B %d, %Y at %I:%M %p")
            except Exception as e:
                logging.warning(f"Could not format booking time: {e}")

        if not msg_type:
            logging.warning("Missing message_type in RabbitMQ message")
            return

        # Format the message based on the event type
        message_template = MESSAGE_TEMPLATES.get(msg_type, "Notification: {msg_type}")
        formatted_message = message_template.format(
            username=username,
            reservation_id=reservation_id,
            order_id=order_id,
            refund_amount=refund_amount,
            table_no=table_no,
            restaurant_name=restaurant_name,
            booking_time=booking_time,
            driver_name=driver_name,  
            customer_name=customer_name,  
        )

        subject = EVENT_SUBJECTS.get(msg_type, f"FeastFinder Notification - {msg_type}")

        logging.info(f"Processing {msg_type} event for {recipient_email}...")
        email_result = send_email(recipient_email, subject, formatted_message)

        # Save the notification to the database
        save_notification_to_db(formatted_message, msg_type, email_result["status"] in ["success", "skipped"])

        if email_result["status"] == "success":
            logging.info(f"Email sent successfully for {msg_type}")
        elif email_result["status"] == "skipped":
            logging.info(f"Email sending skipped (no RESEND_API_KEY set) for {msg_type}")
        else:
            logging.error(f"Failed to send email for {msg_type}: {email_result.get('error')}")
    except Exception as e:
        logging.error(f"Error processing RabbitMQ message: {e}")

# Connect to RabbitMQ
def connect_to_rabbitmq():
    """Connect to RabbitMQ and return connection and channel"""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                heartbeat=300,
                blocked_connection_timeout=300
            )
        )
        channel = connection.channel()
        
        # Ensure exchange exists
        channel.exchange_declare(
            exchange=RABBITMQ_EXCHANGE,
            exchange_type=RABBITMQ_EXCHANGE_TYPE,
            durable=True
        )
        
        return connection, channel
    except Exception as e:
        logging.error(f"Error connecting to RabbitMQ: {e}")
        return None, None

def start_rabbitmq_consumer():
    while True:
        try:
            logging.info("Connecting to RabbitMQ...")
            connection, channel = connect_to_rabbitmq()
            
            if not connection or not channel:
                logging.error("Failed to connect to RabbitMQ. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            queues = {
                "Order_Confirmation": "order.confirmation",
                "Reservation_Confirmation": "reservation.confirmation",
                "Reservation_Cancellation": "reservation.cancellation",
                "Reservation_Decline": "reservation.decline",
                "Reallocation_Notice": "reallocation.notice",
                "Reallocation_Confirmation": "reallocation.confirmation",
                "Waitlist_Notification": "waitlist.notification",
                "Delivery_Order_Accepted" : "delivery.order.accepted",
                "Delivery_Order_Pickedup" : "delivery.order.pickedup",
                "Delivery_Order_Delivered" : "delivery.order.delivered",
                "Delivery_Order_Confirmation" : "delivery.order.confirmation"
            }

            for queue_name, routing_key in queues.items():
                logging.info(f"Consuming from queue: {queue_name}")
                channel.queue_declare(queue=queue_name, durable=True)
                channel.queue_bind(
                    exchange=RABBITMQ_EXCHANGE,
                    queue=queue_name,
                    routing_key=routing_key,
                )
                channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=rabbitmq_callback,
                    auto_ack=True,
                )

            logging.info("Waiting for messages...")
            channel.start_consuming()
        except pika.exceptions.ConnectionClosedByBroker:
            logging.warning("Connection closed by broker. Reconnecting...")
            time.sleep(5)
            continue
        except KeyboardInterrupt:
            logging.info("Stopping RabbitMQ consumer...")
            break
        except Exception as e:
            logging.error(f"Unexpected error in RabbitMQ consumer: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Start RabbitMQ consumer in a separate thread
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=True)