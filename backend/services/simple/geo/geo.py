from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from supabase import create_client
from math import radians, sin, cos, sqrt, atan2
import requests
import time
from datetime import datetime

load_dotenv()

app = Flask(__name__)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Configure Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/api/geo/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "geo-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# Cache of address -> coordinates, so the same address is only ever looked up once.
# A delivery batch repeats the same handful of restaurant/customer addresses many
# times over, and each miss costs a network round trip plus the rate-limit sleep.
_geocode_cache = {}

# Geocoding function
def geocode_address(address):

    #Converts an address into a coordinate string "(latitude,longitude)" using OpenStreetMap Nominatim API.
    #:param address: The address to geocode (e.g., "123 Test St").
    #:return: A string in the format "(latitude,longitude)", or None if geocoding fails.

    if address in _geocode_cache:
        return _geocode_cache[address]

    coordinates = _geocode_uncached(address)
    _geocode_cache[address] = coordinates

    # Nominatim asks for at most 1 request/sec. Sleep only after a real lookup,
    # so cache hits cost nothing.
    time.sleep(1)
    return coordinates


def _geocode_uncached(address):
    # Hardcoded coordinates for common addresses in Singapore if API fails. (fallback)
    hardcoded_locations = {
        "30 Victoria St": "1.29548985,103.8520116901307",
        "973 Upper Serangoon Rd": "1.3738,103.8783",
        "313 Orchard Road": "1.3010188,103.83850574470645",
        "145 Syed Alwi Road": "1.3101174,103.8553229",
        "Tampines Central 5": "1.3531766,103.9449275",
    }
    
    # Restrict results to Singapore only (this stupid thing is having seizures every time ffs)
    try:
        print(f"Geocoding address: {address}")
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": "sg"  
        }
        headers = {
            "User-Agent": "FeastFinder/1.0 (your-delivery@example.com)"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()

        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            coordinates = f"{lat},{lon}"
            print(f"Coordinates for {address}: {coordinates}")
            return coordinates
        else:
            print(f"Geocoding failed for address: {address}")
            
            # Check if we have hardcoded coordinates for this address
            if address in hardcoded_locations:
                print(f"Using hardcoded coordinates for {address}: {hardcoded_locations[address]}")
                return hardcoded_locations[address]
            
            # Final fallback to 30 Victoria St coordinates
            print(f"Using final fallback (30 Victoria St) coordinates for {address}")
            return "1.29548985,103.8520116901307"  
        
    except Exception as e:
        print(f"Error during geocoding: {str(e)}")
        
        # Check if we have hardcoded coordinates for this address
        if address in hardcoded_locations:
            print(f"Using hardcoded coordinates for {address}: {hardcoded_locations[address]}")
            return hardcoded_locations[address]
            
        # Final fallback to 30 Victoria St coordinates
        print(f"Using final fallback (30 Victoria St) coordinates for {address}")
        return "1.29548985,103.8520116901307"  
    
def calculate_distance(lat1, lon1, lat2, lon2):
    #Calculate the distance between two GPS coordinates using the Haversine formula.
    #Returns the distance in kilometers.
    R = 6371.0  # Earth radius in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

@app.route("/api/nearby-restaurants", methods=['POST'])
def find_nearby_restaurants():
    
    #Find restaurants within a specified radius of the driver's location.
    #Return detailed information about nearby restaurants and orders, including coordinates for all entities.
    #Store results in Supabase for nearby restaurants and orders (avoiding duplicates based on order_id).
    try:
        # Parse the request data
        request_data = request.get_json()
        print(f"Received request data: {request_data}")  # Log the input data
        if not request_data or "data" not in request_data:
            return jsonify({"code": 400, "message": "Invalid request format."}), 400

        # Extract the nested 'data' object
        data = request_data.get("data", {})
        driver = data.get("driver")
        restaurants = data.get("restaurants", [])

        # Validate required fields
        if not driver or not restaurants:
            return jsonify({"code": 400, "message": "Missing required fields."}), 400

        driver_id = driver.get("id")
        live_location = driver.get("location")  # Format: "latitude,longitude"
        # Check if live_location is already in "latitude,longitude" format
        try:
            # Attempt to split into latitude and longitude
            driver_lat, driver_lon = live_location.split(",")
            float(driver_lat)  # Ensure it's a valid number
            float(driver_lon)
        except (ValueError, AttributeError):
            # If not in "latitude,longitude" format, assume it's an address and geocode it
            print(f"Live location is not in coordinates format. Geocoding address: {live_location}")
            geocoded_location = geocode_address(live_location)
            if not geocoded_location:
                return jsonify({"code": 400, "message": "Invalid driver live_location."}), 400
            driver_lat, driver_lon = geocoded_location.split(",")
            
        max_distance_km = 5.0  # Default distance limit

        if not driver_id or not live_location:
            return jsonify({"code": 400, "message": "Missing driver ID or live location."}), 400

        print(f"Driver location: {driver_lat}, {driver_lon}")

        # Delete existing records for the driver
        try:
            supabase.table("geospatial").delete().eq("driver_id", driver_id).execute()
            print(f"Deleted existing records for driver {driver_id}.")
        except Exception as e:
            print(f"Error deleting existing records for driver {driver_id}: {str(e)}")
            return jsonify({"code": 500, "message": "Failed to clean up old geospatial data."}), 500

        # Process restaurants and filter nearby orders
        nearby_restaurants = []
        for restaurant in restaurants:
            restaurant_id = restaurant.get("restaurant_id")
            name = restaurant.get("name")
            location_name = restaurant.get("location")
            orders = restaurant.get("orders", [])

            # Geocode the restaurant's address
            restaurant_coordinates = geocode_address(location_name)
            print(f"Geocoded restaurant {name}: {restaurant_coordinates}")
            if not restaurant_coordinates:
                print(f"Skipping restaurant {name} due to invalid address.")
                continue  # Skip restaurants with invalid addresses

            restaurant_lat, restaurant_lon = restaurant_coordinates.split(",")
            restaurant_distance_km = calculate_distance(driver_lat, driver_lon, restaurant_lat, restaurant_lon)
            print(f"Distance to restaurant {name}: {restaurant_distance_km} km")

            if restaurant_distance_km <= max_distance_km:
                # Geocode customer addresses and include their coordinates
                filtered_orders = []
                for order in orders:
                    customer = order.get("customer", {})
                    customer_location = customer.get("location")
                    customer_coordinates = geocode_address(customer_location)
                    print(f"Geocoded customer at {customer_location}: {customer_coordinates}")
                    if not customer_coordinates:
                        print(f"Skipping customer at {customer_location} due to invalid address.")
                        continue  # Skip customers with invalid addresses

                    # Add the order to the filtered list (no distance calculation for customers)
                    filtered_orders.append({
                        "order_id": order.get("order_id"),
                        "item_name": order.get("item_name"),
                        "customer": {
                            "id": customer.get("id"),
                            "name": customer.get("name"),
                            "location": customer_location,
                            "coordinates": customer_coordinates  # Include customer coordinates
                        }
                    })

                # Add the restaurant to the nearby list if it has valid orders
                if filtered_orders:
                    nearby_restaurants.append({
                        "restaurant_id": restaurant_id,
                        "name": name,
                        "location": location_name,
                        "coordinates": restaurant_coordinates,  # Include restaurant coordinates
                        "distance_km": restaurant_distance_km,  # Include distance from driver to restaurant
                        "orders": filtered_orders
                    })

                    # Insert the record if it doesn't exist
                    for order in filtered_orders:
                        try:
                            supabase.table("geospatial").insert({
                                "driver_id": driver_id,
                                "restaurant_id": restaurant_id,
                                "order_id": order["order_id"],
                                "distance": str(restaurant_distance_km)  # Distance from driver to restaurant
                            }).execute()
                        except Exception as e:
                            print(f"Error inserting into Supabase: {str(e)}")

        print(f"Nearby restaurants: {nearby_restaurants}")  # Log the final result
        # Include the full driver object in the response
        response_data = {
            "code": 200,
            "data": {
                "driver": driver,  # Include the full driver object from the input
                "restaurants": nearby_restaurants
            }
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error finding nearby restaurants: {str(e)}")
        return jsonify({"code": 500, "message": "An error occurred while processing the request."}), 500
    
# delete by id
@app.route("/api/delete-geospatial/<string:order_id>", methods=['DELETE'])
def delete_geospatial(order_id):
    """
    Deletes a record from the geospatial table based on the order_id.
    :param order_id: The ID of the order to delete.
    :return: JSON response indicating success or failure.
    """
    try:
        print(f"Attempting to delete geospatial record for order_id: {order_id}")

        # Delete the record with the given order_id
        response = supabase.table("geospatial").delete().eq("order_id", order_id).execute()

        # Check if the response contains an error
        if hasattr(response, 'error') and response.error:
            print(f"Error deleting geospatial record: {response.error.message}")
            return jsonify({
                "code": 500,
                "message": f"Failed to delete geospatial record: {response.error.message}"
            }), 500

        # If no error, proceed with success response
        print(f"Successfully deleted geospatial record for order_id: {order_id}")
        return jsonify({
            "code": 200,
            "message": f"Geospatial record for order_id {order_id} deleted successfully."
        }), 200

    except Exception as e:
        print(f"Error during geospatial deletion: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"An error occurred: {str(e)}"
        }), 500
    
# Main entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5013))
    print(f"Starting geo service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)


# test (dms endpoint before geo.py (geo.py post test))
# http://localhost:5013/nearby-restaurants
# {
#     "code": 200,
#     "data": {
#         "driver": {
#             "availability": true,
#             "id": "59c0cf4c-3931-4523-a7e5-cead2ff191d5",
#             "location": "1.361411361306812,103.8875486",
#             "name": "dc"
#         },
#         "restaurants": [
#             {
#                 "location": "205 Hougang St 21",
#                 "name": "Ocean View Diner",
#                 "orders": [
#                     {
#                         "customer": {
#                             "id": "ef86fa45-55f9-4b9b-9020-868d1f477d73",
#                             "location": "88 Tanjong Katong Rd",
#                             "name": "testfordriver"
#                         },
#                         "item_name": "Seafood Feast",
#                         "order_id": 84
#                     },
#                     {
#                         "customer": {
#                             "id": "ef86fa45-55f9-4b9b-9020-868d1f477d73",
#                             "location": "88 Tanjong Katong Rd",
#                             "name": "testfordriver"
#                         },
#                         "item_name": "Pizza Unlimited",
#                         "order_id": 85
#                     }
#                 ],
#                 "restaurant_id": 1
#             },
#             {
#                 "location": "313 Orchard Rd",
#                 "name": "Mountain Grill",
#                 "orders": [
#                     {
#                         "customer": {
#                             "id": "ef86fa45-55f9-4b9b-9020-868d1f477d73",
#                             "location": "88 Tanjong Katong Rd",
#                             "name": "testfordriver"
#                         },
#                         "item_name": "Steak Lovers Buffet",
#                         "order_id": 86
#                     }
#                 ],
#                 "restaurant_id": 2
#             }
#         ]
#     }
# }