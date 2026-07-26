from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

app = Flask(__name__)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Database connection
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/restaurant/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "restaurant-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# retrieve all restaurants
@app.route("/api/restaurants", methods=['GET'])
def get_all_restaurants():
    try:
        response = supabase.table('restaurant').select('*').execute()
        # sort by least seats so can test easily (the waitlist and reallocation logic)
        restaurant_list = sorted(response.data, key=lambda x: x.get('capacity', 0)) if response.data else []
        
        if restaurant_list:
            return jsonify({
                "code": 200,
                "data": {
                    "restaurants": restaurant_list
                }
            })
        return jsonify({
            "code": 404,
            "message": "No restaurants found."
        }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"An error occurred: {str(e)}"
        }), 500

# retrieve restaurant using id
@app.route("/api/restaurants/<int:restaurant_id>", methods=['GET'])
def get_restaurant(restaurant_id):
    try:
        response = supabase.table('restaurant').select('*').eq('restaurant_id', restaurant_id).execute()
        restaurant = response.data[0] if response.data else None
        
        if restaurant:
            return jsonify({
                "code": 200,
                "data": restaurant
            })
        return jsonify({
            "code": 404,
            "message": "Restaurant not found."
        }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"An error occurred: {str(e)}"
        }), 500

# filter restaurants by cuisine
@app.route("/api/restaurants/cuisine/<string:cuisine>", methods=['GET'])
def get_restaurants_by_cuisine(cuisine):
    try:
        response = supabase.table('restaurant').select('*').eq('cuisine', cuisine).execute()
        # sort by least seats so can test easily (the waitlist and reallocation logic)
        restaurants = sorted(response.data, key=lambda x: x.get('capacity', 0)) if response.data else []
        
        if restaurants:
            return jsonify({
                "code": 200,
                "data": {
                    "restaurants": restaurants
                }
            })
        return jsonify({
            "code": 404,
            "message": f"No restaurants found with cuisine: {cuisine}"
        }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"An error occurred: {str(e)}"
        }), 500

# check if open 1 = open 0 = close
@app.route("/api/restaurants/availability/<int:availability>", methods=['GET'])
def get_restaurants_by_availability(availability):
    try:
        # Convert integer to boolean for Supabase query
        is_available = bool(availability)
        response = supabase.table('restaurant').select('*').eq('availability', is_available).execute()
        # sort by least seats so can test easily (the waitlist and reallocation logic)
        restaurants = sorted(response.data, key=lambda x: x.get('capacity', 0)) if response.data else []
        
        if restaurants:
            return jsonify({
                "code": 200,
                "data": {
                    "restaurants": restaurants
                }
            })
        else:
            return jsonify({
                "code": 404,
                "message": "No restaurants found with this availability status"
            }), 404
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"An error occurred: {str(e)}"
        }), 500

# Get restaurant capacity and count existing dine-in reservations
@app.route("/api/restaurants/capacity/<int:restaurant_id>", methods=['GET'])
def get_restaurant_capacity(restaurant_id):
    try:
        # Get restaurant details including capacity
        response = supabase.table('restaurant').select('*').eq('restaurant_id', restaurant_id).execute()
        restaurant = response.data[0] if response.data else None
        
        if not restaurant:
            return jsonify({
                "code": 404,
                "message": "Restaurant not found."
            }), 404
            
        restaurant_capacity = restaurant.get("capacity", 0)
        
        # Count existing reservations for this restaurant that have status 'Booked'
        reservation_response = supabase.table('reservation').select('*').eq('restaurant_id', restaurant_id).eq('status', 'Booked').execute()
        reservation_count = len(reservation_response.data) if reservation_response.data else 0
        
        return jsonify({
            "code": 200,
            "data": {
                "restaurant_id": restaurant_id,
                "capacity": restaurant_capacity,
                "current_reservations": reservation_count,
                "available_slots": max(0, restaurant_capacity - reservation_count)
            }
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"An error occurred: {str(e)}"
        }), 500
        
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)