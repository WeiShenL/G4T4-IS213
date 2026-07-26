from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
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
CORS(app, resources={r"/*": {"origins": allowed_origins, "methods": ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]}})

# Database connection
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/menu/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "menu-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# retrieve menu items for a specific restaurant
@app.route("/api/menu/<int:restaurant_id>", methods=['GET'])
def get_restaurant_menu(restaurant_id):
    try:
        response = supabase.table('menu').select('*').eq('restaurant_id', restaurant_id).execute()
        menu_items = response.data
        
        if menu_items:
            return jsonify({
                "code": 200,
                "data": {
                    "menu_items": menu_items
                }
            })
        return jsonify({
            "code": 404,
            "message": f"No menu items found for restaurant ID: {restaurant_id}"
        }), 404
    except Exception as e:
        app.logger.error("Error in get_restaurant_menu: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# get a specific menu item by ID --> NOT USED AS OF NOW
@app.route("/api/menu/item/<int:menu_id>", methods=['GET'])
def get_menu_item(menu_id):
    try:
        response = supabase.table('menu').select('*').eq('menu_id', menu_id).execute()
        menu_item = response.data[0] if response.data else None
        
        if menu_item:
            return jsonify({
                "code": 200,
                "data": menu_item
            })
        return jsonify({
            "code": 404,
            "message": f"Menu item not found with ID: {menu_id}"
        }), 404
    except Exception as e:
        app.logger.error("Error in get_menu_item: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True)