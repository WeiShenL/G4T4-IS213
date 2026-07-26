from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
from supabase import create_client, Client
from datetime import datetime

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
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Database connection
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/order/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "order-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# create a new order with Stripe payment ID
@app.route("/api/orders", methods=['POST'])
def create_order():
    try:
        data = request.json
        required_fields = ['user_id', 'restaurant_id', 'item_name', 'quantity', 'order_price', 'payment_id']
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "code": 400,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Insert order into the database
        new_order = {
            "user_id": data['user_id'],
            "restaurant_id": data['restaurant_id'],
            "item_name": data['item_name'],
            "quantity": data['quantity'],
            "order_price": data['order_price'],
            "payment_id": data['payment_id'],
            "created_at": datetime.now().isoformat(),
            "order_type": data.get('order_type') 
        }
        
        response = supabase.table('orders').insert(new_order).execute()
        
        if response.data:
            return jsonify({
                "code": 201,
                "message": "Order created successfully",
                "data": response.data[0]
            }), 201
        else:
            return jsonify({
                "code": 500,
                "message": "Failed to create order"
            }), 500
    
    except Exception as e:
        app.logger.error("Error in create_order: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# get all orders for a specific user 
@app.route("/api/orders/user/<string:user_id>", methods=['GET'])
def get_user_orders(user_id):
    try:
        response = supabase.table('orders').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        orders = response.data
        
        if orders:
            return jsonify({
                "code": 200,
                "data": {
                    "orders": orders
                }
            })
        return jsonify({
            "code": 404,
            "message": f"No orders found for user: {user_id}"
        }), 404
    except Exception as e:
        app.logger.error("Error in get_user_orders: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# Delete a new route to delete an order by order_id
@app.route("/api/orders/<int:order_id>", methods=['DELETE'])
def delete_order_by_id(order_id):
    try:
        if not order_id:
            return jsonify({
                "code": 400,
                "message": "Order ID is required"
            }), 400
            
        # Delete the order with the given order_id
        delete_response = supabase.table('orders').delete().eq('order_id', order_id).execute()
        
        if delete_response.data:
            return jsonify({
                "code": 200,
                "message": f"Order with ID {order_id} deleted successfully"
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"No order found with ID: {order_id}"
            }), 404
            
    except Exception as e:
        app.logger.error("Error in delete_order_by_id: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# Update order type
@app.route("/api/orders/<int:order_id>/type", methods=['PATCH'])
def update_order_type(order_id):
    try:
        data = request.json
        
        if 'order_type' not in data:
            return jsonify({
                "code": 400,
                "message": "Missing required field: order_type"
            }), 400
            
        # Update the order with the given order_id
        update_data = {
            "order_type": data['order_type']
        }
        
        update_response = supabase.table('orders').update(update_data).eq('order_id', order_id).execute()
        
        if update_response.data:
            return jsonify({
                "code": 200,
                "message": f"Order with ID {order_id} updated successfully",
                "data": update_response.data[0]
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"No order found with ID: {order_id}"
            }), 404
            
    except Exception as e:
        app.logger.error("Error in update_order_type: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# Get orders by restaurant ID and order type
@app.route("/api/orders/restaurant/<int:restaurant_id>/type/<string:order_type>", methods=['GET'])
def get_restaurant_orders_by_type(restaurant_id, order_type):
    try:
        # Query orders with matching restaurant_id and order_type
        response = supabase.table('orders').select('*')\
            .eq('restaurant_id', restaurant_id)\
            .eq('order_type', order_type)\
            .execute()
            
        orders = response.data
        
        if orders:
            return jsonify({
                "code": 200,
                "data": {
                    "orders": orders
                }
            })
        return jsonify({
            "code": 200,
            "data": {
                "orders": []
            }
        })
    except Exception as e:
        app.logger.error("Error in get_restaurant_orders_by_type: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# Fetch orders by order_type
@app.route("/api/orders/type/<string:order_type>", methods=['GET'])
def get_orders_by_type(order_type):
    try:
        # Query orders with the specified order_type
        response = supabase.table('orders').select('*').eq('order_type', order_type).execute()
        orders = response.data
        
        if orders:
            return jsonify({
                "code": 200,
                "data": {
                    "orders": orders
                }
            })
        return jsonify({
            "code": 404,
            "message": f"No orders found with type: {order_type}"
        }), 404
    except Exception as e:
        app.logger.error("Error in get_orders_by_type: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500
    
# get specific order id
@app.route("/api/orders/<int:order_id>", methods=['GET'])
def get_order_by_id(order_id):
    """
    Retrieve a specific order by its order_id.
    """
    try:
        # Query the database for the specific order
        response = supabase.table('orders').select('*').eq('order_id', str(order_id)).execute()
        order = response.data

        if order:
            return jsonify({
                "code": 200,
                "data": order[0]
            })
        else:
            return jsonify({
                "code": 404,
                "message": f"Order with ID {order_id} not found."
            }), 404

    except Exception as e:
        app.logger.error("Error in get_order_by_id: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    print(f"Starting order service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)