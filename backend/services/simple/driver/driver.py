from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Load environment variables
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

# Supabase configuration
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/driver/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "driver-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# Get driver by ID
@app.route("/api/driver/<string:driver_id>", methods=['GET'])
def get_driver(driver_id):
    try:
        # Query the driver_profiles table using the provided driver_id
        response = supabase.table('driver_profiles').select('*').eq('id', driver_id).execute()
        
        # Check if any data was returned
        if not response.data:
            return jsonify({
                "code": 404,
                "message": f"Driver not found with ID: {driver_id}"
            }), 404
        
        # Return the driver's profile
        return jsonify({
            "code": 200,
            "data": response.data[0]
        })
    
    except Exception as e:
        app.logger.error("Error in get_driver: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5011))
    print(f"Starting driver service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)