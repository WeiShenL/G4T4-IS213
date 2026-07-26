from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import stripe
from datetime import datetime
from supabase import create_client, Client

import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error("Unhandled Exception: %s", str(e), exc_info=True)
    return jsonify({"error": "An internal server error occurred"}), 500

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": allowed_origins, "methods": ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]}})

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
print(f"Stripe API configured with key: {stripe.api_key[:5]}...")
webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
print(f"Webhook secret configured: {webhook_secret[:5]}..." if webhook_secret else "Webhook secret not configured (Stripe webhooks disabled)")

# Database connection
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/payment/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "payment-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# Process a refund with idempotency check
@app.route("/api/payment/refund", methods=['POST'])
def process_refund():
    try:
        data = request.json
        payment_id = data.get('payment_id')
        amount = data.get('amount')

        if not payment_id:
            return jsonify({
                "code": 400,
                "message": "Payment ID is required"
            }), 400

        # IDEMPOTENCY CHECK: Check if this payment has already been refunded
        existing_payment = supabase.table('payments').select('*').eq('stripe_payment_id', payment_id).execute()

        if existing_payment.data:
            payment_record = existing_payment.data[0]
            if payment_record.get('status') == 'refunded':
                print(f"Payment {payment_id} has already been refunded. Returning cached result.")
                return jsonify({
                    "code": 200,
                    "refund": {
                        "id": f"cached_refund_{payment_id}",
                        "amount": int(payment_record.get('amount', 0) * 100),  # Convert back to cents
                        "status": "succeeded"
                    },
                    "message": "Refund was already processed (idempotent response)"
                })

        # Process the refund through Stripe
        refund_params = {
            "payment_intent": payment_id,
        }

        # Add amount if provided
        if amount:
            refund_params["amount"] = int(amount)

        print(f"Processing refund for payment intent: {payment_id}")

        refund = stripe.Refund.create(**refund_params)

        print(f"Refund processed: {refund.id}")

        # Update payment status to 'refunded' in database for idempotency
        if existing_payment.data:
            supabase.table('payments').update({
                'status': 'refunded'
            }).eq('stripe_payment_id', payment_id).execute()
        else:
            # If no record exists, create one with refunded status
            supabase.table('payments').insert({
                'stripe_payment_id': payment_id,
                'amount': refund.amount / 100,
                'status': 'refunded',
                'created_at': datetime.now().isoformat()
            }).execute()

        return jsonify({
            "code": 200,
            "refund": {
                "id": refund.id,
                "amount": refund.amount,
                "status": refund.status
            }
        })

    except stripe.error.InvalidRequestError as e:
        # Handle Stripe-specific errors (e.g., already refunded)
        error_message = str(e)
        print(f"Stripe error processing refund: {error_message}")

        if "has already been refunded" in error_message.lower():
            # Mark as refunded in our database
            if payment_id:
                supabase.table('payments').update({
                    'status': 'refunded'
                }).eq('stripe_payment_id', payment_id).execute()

            return jsonify({
                "code": 200,
                "refund": {
                    "id": f"already_refunded_{payment_id}",
                    "amount": 0,
                    "status": "succeeded"
                },
                "message": "Payment was already refunded through Stripe"
            })

        return jsonify({
            "code": 400,
            "message": f"Stripe error: {error_message}"
        }), 400

    except Exception as e:
        app.logger.error("Error processing refund: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# Create a checkout session
@app.route("/api/payment/create-checkout-session", methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        
        # Extract order details
        order_details = data.get('orderDetails')
        customer_id = data.get('customerId')
        success_url = data.get('successUrl')
        cancel_url = data.get('cancelUrl')
        
        # Validate required parameters
        if not all([order_details, customer_id, success_url, cancel_url]):
            return jsonify({
                "code": 400,
                "message": "Missing required parameters"
            }), 400
        
        # Format line items for Stripe
        line_items = [{
            'price_data': {
                'currency': order_details.get('currency', 'usd'),
                'product_data': {
                    'name': order_details.get('itemName', 'Food Order'),
                    'description': f"From {order_details.get('restaurantName', 'Restaurant')}",
                },
                'unit_amount': int(order_details.get('amount') / order_details.get('quantity')),  # in cents
            },
            'quantity': order_details.get('quantity', 1),
        }]
        
        # Add metadata to the session
        metadata = {
            'restaurantId': str(order_details.get('restaurantId')),
            'restaurantName': order_details.get('restaurantName'),
            'userId': customer_id
        }
        
        print(f"Creating Stripe checkout session with line items: {line_items}")
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )
        
        print(f"Checkout session created: {session.id}")
        
        return jsonify({
            "code": 200,
            "sessionId": session.id,
            "url": session.url
        })
    
    except Exception as e:
        app.logger.error("Error creating checkout session: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# Verify payment and update payment db for logging purposes
@app.route("/api/payment/verify-payment/<string:session_id>", methods=['GET'])
def verify_payment(session_id):
    try:
        print(f"Verifying payment for session: {session_id}")
        
        # Retrieve the session
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Check if payment was successful
        if session.payment_status != 'paid':
            return jsonify({
                "code": 400,
                "message": "Payment not completed"
            }), 400
        
        # Get the payment intent
        payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        
        # Store payment record in the database
        payment_record = {
            "stripe_payment_id": payment_intent.id,
            "amount": payment_intent.amount / 100,  # Convert cents to dollars
            "status": payment_intent.status,
            "created_at": datetime.now().isoformat()
        }
        
        # Insert payment record into the database
        response = supabase.table('payments').insert(payment_record).execute()
        
        if not response.data:
            print(f"Warning: Failed to save payment record to database")
        
        print(f"Payment verified: {payment_intent.id} with status {payment_intent.status}")
        
        return jsonify({
            "code": 200,
            "paymentIntent": {
                "id": payment_intent.id,
                "status": payment_intent.status,
                "amount": payment_intent.amount,
                "created_at": datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        app.logger.error("Error verifying payment: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5006))
    print(f"Starting payment service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)