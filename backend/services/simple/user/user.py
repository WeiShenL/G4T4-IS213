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
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Database connection
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/user/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "user-service",
        "timestamp": datetime.now().isoformat()
    }), 200
    
# Get user details by user_id
@app.route("/api/user/<string:user_id>", methods=['GET'])
def get_user(user_id):
    try:
        response = supabase.table('customer_profiles').select('*').eq('id', user_id).execute()
        
        if not response.data:
            return jsonify({
                "code": 404,
                "message": f"User not found with ID: {user_id}"
            }), 404
            
        return jsonify({
            "code": 200,
            "data": response.data[0]
        })
    except Exception as e:
        app.logger.error("Error in get_user: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting user service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)