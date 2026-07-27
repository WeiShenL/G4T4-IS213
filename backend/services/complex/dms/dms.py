from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import logging

load_dotenv()

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

# Base URLs for the services
ORDER_SERVICE_URL = os.getenv('ORDER_SERVICE_URL', 'http://order-service:5000')
DRIVER_SERVICE_URL = os.getenv('DRIVER_SERVICE_URL', 'http://driver-service:5000')
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://user-service:5000')
RESTAURANT_SERVICE_URL = os.getenv('RESTAURANT_SERVICE_URL', 'http://restaurant-service:5000')
DRIVERDETAIL_SERVICE_URL = os.getenv('DRIVERDETAIL_SERVICE_URL', 'http://driver-details-service:5000')
GEOCODING_SERVICE_URL = os.getenv('GEOCODING_SERVICE_URL', 'http://geo-service:5000')

# Never let a single unresponsive dependency hang this endpoint indefinitely.
# The geocoding fan-out is inherently slower than a plain lookup, so it gets its own budget.
SERVICE_TIMEOUT = int(os.getenv('SERVICE_TIMEOUT', '10'))
GEO_TIMEOUT = int(os.getenv('GEO_TIMEOUT', '60'))

def get_driver_address(driver_id):
    #Fetch the driver's address from the DRIVER_SERVICE_URL.
    #:param driver_id: The ID of the driver.
    #:return: The driver's address (string) or None if not found.
    try:
        driver_response = requests.get(f"{DRIVER_SERVICE_URL}/api/driver/{driver_id}", timeout=SERVICE_TIMEOUT)
        if driver_response.status_code == 200:
            driver_data = driver_response.json().get("data", {})
            return driver_data.get("street_address", None)  # key for the driver's address
        else:
            print(f"Failed to fetch driver address for driver_id: {driver_id}. Status code: {driver_response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching driver address: {str(e)}")
        return None

@app.route("/api/dms/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "dms-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
@app.route("/api/delivery-management", methods=['GET'])
def get_delivery_management_data():
    try:
        # Get driver_id from query parameter (required)
        driver_id = request.args.get("driver_id")
        if not driver_id:
            return jsonify({"code": 400, "message": "Missing driver_id."}), 400

        # Fetch the logged-in driver's details
        driver_response = requests.get(f"{DRIVER_SERVICE_URL}/api/driver/{driver_id}", timeout=SERVICE_TIMEOUT)
        if driver_response.status_code != 200:
            return jsonify({"code": 404, "message": "Driver not found."}), 404
        driver_data = driver_response.json().get("data", {})

        # Fetch all delivery orders (regardless of driver assignment)
        order_response = requests.get(f"{ORDER_SERVICE_URL}/api/orders/type/delivery", timeout=SERVICE_TIMEOUT)
        if order_response.status_code == 404:
            delivery_orders = []
        elif order_response.status_code != 200:
            return jsonify({"code": 500, "message": "Failed to fetch delivery orders."}), 500
        else:
            delivery_orders = order_response.json().get("data", {}).get("orders", [])

        if not delivery_orders:
            # Return empty restaurants list with 200 status code instead of 500 error
            return jsonify({
                "code": 200,
                "data": {
                    "driver": {
                        "id": driver_id,
                        "name": driver_data.get("driver_name", "Unknown"),
                        "location": get_driver_address(driver_id) or "Unknown",
                        "availability": True
                    },
                    "restaurants": []
                }
            }), 200

        # Group orders by restaurant
        restaurants = {}  # Key: restaurant_id, Value: {restaurant details + orders}
        customers = {}    # Key: customer_id, Value: customer details (many orders share a customer)

        for order in delivery_orders:
            restaurant_id = order.get("restaurant_id")
            customer_id = order.get("user_id")

            # Fetch restaurant details if not already cached
            if restaurant_id not in restaurants:
                restaurant_resp = requests.get(f"{RESTAURANT_SERVICE_URL}/api/restaurants/{restaurant_id}", timeout=SERVICE_TIMEOUT)
                restaurant_data = restaurant_resp.json().get("data") if restaurant_resp.status_code == 200 else None
                if not restaurant_data:
                    continue  # Skip invalid restaurants

                restaurants[restaurant_id] = {
                    "restaurant_id": restaurant_id,
                    "name": restaurant_data.get("name", "Unknown"),
                    "location": restaurant_data.get("address", "Unknown"),
                    "orders": []
                }

            # Fetch customer details if not already cached
            if customer_id not in customers:
                customer_resp = requests.get(f"{USER_SERVICE_URL}/api/user/{customer_id}", timeout=SERVICE_TIMEOUT)
                customers[customer_id] = customer_resp.json().get("data") if customer_resp.status_code == 200 else None
            customer_data = customers[customer_id]

            # Build order details 
            order_details = {
                "order_id": order.get("order_id"),
                "item_name": order.get("item_name"),
                "customer": {
                    "id": customer_id,
                    "name": customer_data.get("customer_name", "Unknown") if customer_data else "Unknown",
                    "location": customer_data.get("street_address", "Unknown") if customer_data else "Unknown"
                }
            }

            # Append order to the restaurant's orders list
            restaurants[restaurant_id]["orders"].append(order_details)

        # Convert restaurants dictionary to list
        restaurant_list = list(restaurants.values())

        # Fetch detailed driver details from the driverdetails service
        detailed_driver_response = requests.get(f"{DRIVERDETAIL_SERVICE_URL}/api/driverdetails/{driver_id}", timeout=SERVICE_TIMEOUT)
        if detailed_driver_response.status_code == 404:  # Driver details not found, create a new record
            print(f"No driver details found for driver_id: {driver_id}. Creating a new record.")

            # Fetch the driver's address
            driver_address = get_driver_address(driver_id)
            if not driver_address:
                return jsonify({"code": 404, "message": "Driver's address not found."}), 404

            # Create a new driver details record with the address as the default live_location
            new_driver_payload = {
                "driver_id": driver_id,
                "live_location": driver_address,
                "availability": True
            }
            create_response = requests.post(f"{DRIVERDETAIL_SERVICE_URL}/api/driverdetails", json=new_driver_payload, timeout=SERVICE_TIMEOUT)
            if create_response.status_code not in [200, 201]:
                print(f"Error creating driver details: {create_response.status_code}, {create_response.text}")
                return jsonify({"code": 500, "message": "Failed to create driver details."}), 500

            # Extract the newly created driver details
            detailed_driver_data = create_response.json().get("data", {})
        elif detailed_driver_response.status_code in [200, 201]:  # Driver details exist
            detailed_driver_data = detailed_driver_response.json().get("data", {})
        else:
            print(f"Error fetching driver details: {detailed_driver_response.status_code}, {detailed_driver_response.text}")
            return jsonify({"code": 500, "message": "Failed to fetch driver details."}), 500

        # Combine driver details (basic + detailed)

        driver_details = {
            "id": driver_id,
            "name": driver_data.get("driver_name", "Unknown"),  # From old driver service
            "location": detailed_driver_data.get("live_location", None),  # From driverdetails service
            "availability": detailed_driver_data.get("availability", True)  # From driverdetails service
        }

        # If live_location is None, fetch the driver's address as fallback
        if not driver_details["location"]:
            driver_address = get_driver_address(driver_id)
            if driver_address:
                driver_details["location"] = driver_address  # Pass the raw address
                print(f"Default live_location set to driver's address: {driver_address}")
            else:
                return jsonify({"code": 404, "message": "Driver's address not found."}), 404
            
        
        # Call the geocoding service to filter nearby restaurants
        geo_payload = {
            "data": {
                "driver": driver_details,
                "restaurants": restaurant_list
            }
        }
        geo_response = requests.post(f"{GEOCODING_SERVICE_URL}/api/nearby-restaurants", json=geo_payload, timeout=GEO_TIMEOUT)
        if geo_response.status_code != 200:
            print(f"Error calling geocoding service: {geo_response.status_code}, {geo_response.text}")
            return jsonify({"code": 500, "message": "Failed to fetch nearby restaurants."}), 500

        # Return the response from the geocoding service
        return geo_response.json()

    except Exception as e:
        app.logger.error("Error fetching delivery management data: %s", str(e), exc_info=True)
        return jsonify({"code": 500, "message": "An internal server error occurred"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5014))
    print(f"Starting Delivery Management Service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)