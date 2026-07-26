from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

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

# Database connection
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/waitlist/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "waitlist-service",
        "timestamp": datetime.now().isoformat()
    }), 200


# Add user to waitlist
# POST /api/waitlist/addUser
# Body: {"user_id": "uuid", "restaurant_id": int}
# Response: {"Id": int, "user_id": "uuid", "time": "ISO timestamp", "restaurant_id": int}
@app.route("/api/waitlist/addUser", methods=['POST'])
def add_user_to_waitlist():
    try:
        data = request.json

        # Validate required fields
        if not data.get('user_id'):
            return jsonify({
                "Id": 0,
                "user_id": "0",
                "time": datetime.utcnow().isoformat() + "Z",
                "restaurant_id": 0
            }), 200

        if not data.get('restaurant_id'):
            return jsonify({
                "Id": 0,
                "user_id": "0",
                "time": datetime.utcnow().isoformat() + "Z",
                "restaurant_id": 0
            }), 200

        user_id = data['user_id']
        restaurant_id = data['restaurant_id']
        current_time = datetime.utcnow().isoformat() + "Z"

        # Check if user is already in waitlist for this restaurant
        existing = supabase.table('waitlist').select('*').eq('user_id', user_id).eq('restaurant_id', restaurant_id).execute()

        if existing.data:
            # User already in waitlist, return existing entry
            entry = existing.data[0]
            return jsonify({
                "Id": entry['waitlist_id'],
                "user_id": entry['user_id'],
                "time": entry['timestamp_added'],
                "restaurant_id": entry['restaurant_id']
            }), 200

        # Insert new waitlist entry
        new_entry = {
            "user_id": user_id,
            "restaurant_id": restaurant_id,
            "timestamp_added": current_time,
            "status": "waiting"
        }

        response = supabase.table('waitlist').insert(new_entry).execute()

        if response.data:
            entry = response.data[0]
            return jsonify({
                "Id": entry['waitlist_id'],
                "user_id": entry['user_id'],
                "time": entry['timestamp_added'],
                "restaurant_id": entry['restaurant_id']
            }), 200
        else:
            # Return 0 values on failure (matching OutSystems behavior)
            return jsonify({
                "Id": 0,
                "user_id": "0",
                "time": current_time,
                "restaurant_id": 0
            }), 200

    except Exception as e:
        print(f"Error adding user to waitlist: {str(e)}")
        # Return 0 values on error (matching OutSystems behavior)
        return jsonify({
            "Id": 0,
            "user_id": "0",
            "time": datetime.utcnow().isoformat() + "Z",
            "restaurant_id": 0
        }), 200


# Get next user in waitlist (priority customer - FIFO based on timestamp)
# GET /api/waitlist/Get_nextUser?restaurant_id={restaurant_id}
# Response: {"Id": int, "user_id": "uuid", "time": "ISO timestamp", "restaurant_id": int}
# NOTE: This now marks the entry as 'processing' instead of deleting immediately.
# Call /api/waitlist/confirm/{waitlist_id} after successful reallocation to delete.
# Call /api/waitlist/release/{waitlist_id} if reallocation fails to return to waiting.
@app.route("/api/waitlist/Get_nextUser", methods=['GET'])
def get_next_user():
    try:
        restaurant_id = request.args.get('restaurant_id')

        if not restaurant_id:
            return jsonify({
                "Id": 0,
                "user_id": "0",
                "time": datetime.utcnow().isoformat() + "Z",
                "restaurant_id": 0
            }), 200

        # Get the first user in waitlist for this restaurant (ordered by timestamp - FIFO)
        # Only select entries with status='waiting' to prevent race conditions
        response = supabase.table('waitlist').select('*').eq('restaurant_id', restaurant_id).eq('status', 'waiting').order('timestamp_added', desc=False).limit(1).execute()

        if response.data and len(response.data) > 0:
            entry = response.data[0]

            # Mark as 'processing' instead of deleting - prevents race condition
            # and allows recovery if reallocation fails
            update_response = supabase.table('waitlist').update({
                'status': 'processing'
            }).eq('waitlist_id', entry['waitlist_id']).eq('status', 'waiting').execute()

            # Check if update was successful (another request might have grabbed it)
            if not update_response.data:
                # Someone else got this entry, try to get the next one
                print(f"Waitlist entry {entry['waitlist_id']} already claimed, retrying...")
                # Recursive call to try again with the next entry
                return get_next_user()

            return jsonify({
                "Id": entry['waitlist_id'],
                "user_id": entry['user_id'],
                "time": entry['timestamp_added'],
                "restaurant_id": entry['restaurant_id']
            }), 200
        else:
            # No users in waitlist - return 0 values (matching OutSystems behavior)
            return jsonify({
                "Id": 0,
                "user_id": "0",
                "time": datetime.utcnow().isoformat() + "Z",
                "restaurant_id": int(restaurant_id) if restaurant_id else 0
            }), 200

    except Exception as e:
        print(f"Error getting next user from waitlist: {str(e)}")
        return jsonify({
            "Id": 0,
            "user_id": "0",
            "time": datetime.utcnow().isoformat() + "Z",
            "restaurant_id": 0
        }), 200


# Confirm waitlist entry removal after successful reallocation
# DELETE /api/waitlist/confirm/{waitlist_id}
# Call this after reallocation succeeds to permanently remove the entry
@app.route("/api/waitlist/confirm/<int:waitlist_id>", methods=['DELETE'])
def confirm_waitlist_removal(waitlist_id):
    try:
        # Only delete if status is 'processing' (prevents accidental deletions)
        delete_response = supabase.table('waitlist').delete().eq('waitlist_id', waitlist_id).eq('status', 'processing').execute()

        if delete_response.data:
            return jsonify({
                "code": 200,
                "message": f"Waitlist entry {waitlist_id} confirmed and removed."
            }), 200
        else:
            return jsonify({
                "code": 404,
                "message": f"Waitlist entry {waitlist_id} not found or not in processing state."
            }), 404

    except Exception as e:
        app.logger.error("Error confirming waitlist removal: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500


# Release a processing waitlist entry back to waiting status
# PATCH /api/waitlist/release/{waitlist_id}
# Call this if reallocation fails to return the user to the waitlist
@app.route("/api/waitlist/release/<int:waitlist_id>", methods=['PATCH'])
def release_waitlist_entry(waitlist_id):
    try:
        # Reset status to 'waiting' so user can be picked up again
        update_response = supabase.table('waitlist').update({
            'status': 'waiting'
        }).eq('waitlist_id', waitlist_id).eq('status', 'processing').execute()

        if update_response.data:
            return jsonify({
                "code": 200,
                "message": f"Waitlist entry {waitlist_id} released back to waiting."
            }), 200
        else:
            return jsonify({
                "code": 404,
                "message": f"Waitlist entry {waitlist_id} not found or not in processing state."
            }), 404

    except Exception as e:
        app.logger.error("Error releasing waitlist entry: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500


# Get all waitlist entries for a restaurant
# GET /api/waitlist/restaurant/{restaurant_id}
@app.route("/api/waitlist/restaurant/<int:restaurant_id>", methods=['GET'])
def get_waitlist_by_restaurant(restaurant_id):
    try:
        response = supabase.table('waitlist').select('*').eq('restaurant_id', restaurant_id).eq('status', 'waiting').order('timestamp_added', desc=False).execute()

        if response.data:
            # Transform to match expected format
            waitlist = []
            for entry in response.data:
                waitlist.append({
                    "Id": entry['waitlist_id'],
                    "user_id": entry['user_id'],
                    "time": entry['timestamp_added'],
                    "restaurant_id": entry['restaurant_id']
                })
            return jsonify({
                "code": 200,
                "data": {
                    "waitlist": waitlist,
                    "count": len(waitlist)
                }
            }), 200
        return jsonify({
            "code": 200,
            "data": {
                "waitlist": [],
                "count": 0
            }
        }), 200

    except Exception as e:
        app.logger.error("Error fetching waitlist by restaurant: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500


# Get waitlist entries for a specific user
# GET /api/waitlist/user/{user_id}
@app.route("/api/waitlist/user/<string:user_id>", methods=['GET'])
def get_waitlist_by_user(user_id):
    try:
        response = supabase.table('waitlist').select('*').eq('user_id', user_id).eq('status', 'waiting').order('timestamp_added', desc=False).execute()

        if response.data:
            waitlist = []
            for entry in response.data:
                waitlist.append({
                    "Id": entry['waitlist_id'],
                    "user_id": entry['user_id'],
                    "time": entry['timestamp_added'],
                    "restaurant_id": entry['restaurant_id']
                })
            return jsonify({
                "code": 200,
                "data": {
                    "waitlist": waitlist,
                    "count": len(waitlist)
                }
            }), 200
        return jsonify({
            "code": 200,
            "data": {
                "waitlist": [],
                "count": 0
            }
        }), 200

    except Exception as e:
        app.logger.error("Error fetching waitlist by user: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500


# Remove user from waitlist
# DELETE /api/waitlist/{waitlist_id}
@app.route("/api/waitlist/<int:waitlist_id>", methods=['DELETE'])
def delete_waitlist_entry(waitlist_id):
    try:
        # Check if entry exists
        response = supabase.table('waitlist').select('*').eq('waitlist_id', waitlist_id).execute()

        if not response.data:
            return jsonify({
                "code": 404,
                "message": f"Waitlist entry with ID {waitlist_id} not found."
            }), 404

        # Delete the entry
        delete_response = supabase.table('waitlist').delete().eq('waitlist_id', waitlist_id).execute()

        if delete_response.data:
            return jsonify({
                "code": 200,
                "message": f"Waitlist entry {waitlist_id} deleted successfully."
            }), 200
        else:
            return jsonify({
                "code": 500,
                "message": "Failed to delete waitlist entry."
            }), 500

    except Exception as e:
        app.logger.error("Error deleting waitlist entry: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500


# Remove user from waitlist by user_id and restaurant_id
# DELETE /api/waitlist/remove
# Body: {"user_id": "uuid", "restaurant_id": int}
@app.route("/api/waitlist/remove", methods=['DELETE'])
def remove_user_from_waitlist():
    try:
        data = request.json
        user_id = data.get('user_id')
        restaurant_id = data.get('restaurant_id')

        if not user_id or not restaurant_id:
            return jsonify({
                "code": 400,
                "message": "Missing required fields: user_id and restaurant_id"
            }), 400

        # Find and delete the entry
        response = supabase.table('waitlist').select('*').eq('user_id', user_id).eq('restaurant_id', restaurant_id).execute()

        if not response.data:
            return jsonify({
                "code": 404,
                "message": "User not found in waitlist for this restaurant."
            }), 404

        delete_response = supabase.table('waitlist').delete().eq('user_id', user_id).eq('restaurant_id', restaurant_id).execute()

        if delete_response.data:
            return jsonify({
                "code": 200,
                "message": "User removed from waitlist successfully."
            }), 200
        else:
            return jsonify({
                "code": 500,
                "message": "Failed to remove user from waitlist."
            }), 500

    except Exception as e:
        app.logger.error("Error removing user from waitlist: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5016))
    print(f"Starting waitlist service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
