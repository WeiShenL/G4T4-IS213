#!/usr/bin/env python3

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from uuid import UUID
import requests
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

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@app.route("/api/driverdetails/health", methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "driver-details-service",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/api/driverdetails/<uuid:driver_id>", methods=['GET'])
def get_driver_details_by_id(driver_id):
    """
    Retrieve driver details for a specific driver_id from Supabase.
    If no record exists, create one with default values.
    """
    try:
        # Step 1: Convert driver_id to string (required for Supabase queries)
        driver_id_str = str(driver_id)

        # Step 2: Check if the driver exists in the database
        response = supabase.table("driverdetails").select("*").eq("driver_id", driver_id_str).execute()
        driver_detail = response.data

        if driver_detail:
            # Return existing driver details
            return jsonify(
                {
                    "code": 200,
                    "data": driver_detail[0]
                }
            )

        # Step 3: Create a new record if the driver doesn't exist
        print(f"No driver found for driver_id: {driver_id}. Creating a new record.")

        new_driver_detail = {
            "driver_id": driver_id_str,  # Ensure UUID is converted to string
            "live_location": None,       # Default value
            "availability": True,        # Default value
            "total_deliveries": 0,       # Default value for new column
            "total_earnings": 0.00       # Default value for new column
        }

        # Attempt to insert the new record
        create_response = supabase.table("driverdetails").insert(new_driver_detail).execute()

        # Log the insertion result
        print(f"Insertion result: {create_response}")

        # Return the newly created driver details
        return jsonify(
            {
                "code": 201,
                "message": "Driver details created successfully.",
                "data": create_response.data[0]
            }
        ), 201

    except Exception as e:
        app.logger.error("Error fetching/creating driver details: %s", str(e), exc_info=True)
        return jsonify(
            {
                "code": 500,
                "message": "An internal server error occurred"
            }
        ), 500
    

@app.route("/api/driverdetails/<uuid:driver_id>", methods=['PATCH'])
def update_driver_availability(driver_id):
    try:
        # Step 1: Convert driver_id to string (required for Supabase queries)
        driver_id_str = str(driver_id)

        # Step 2: Parse the request body
        data = request.json or {}
        availability = data.get("availability")

        if availability is None:
            return jsonify(
                {
                    "code": 400,
                    "message": "Missing 'availability' field in request body."
                }
            ), 400

        # Step 3: Attempt to update the driver's availability
        update_response = supabase.table("driverdetails").update({"availability": availability}).eq("driver_id", driver_id_str).execute()

        # Step 4: Check if the update was successful
        if not update_response.data:
            return jsonify(
                {
                    "code": 404,
                    "message": f"Driver with ID {driver_id_str} not found or no rows updated."
                }
            ), 404

        # Step 5: Return success response
        return jsonify(
            {
                "code": 200,
                "message": "Driver availability updated successfully.",
                "data": update_response.data[0]
            }
        ), 200

    except Exception as e:
        app.logger.error("Error updating driver availability: %s", str(e), exc_info=True)
        return jsonify(
            {
                "code": 500,
                "message": "An internal server error occurred"
            }
        ), 500


@app.route("/api/driverdetails/<uuid:driver_id>/complete-delivery", methods=['PATCH'])
def update_delivery_completion(driver_id):
    try:
        # Convert driver_id to string (required for Supabase queries)
        driver_id_str = str(driver_id)
        
        # Default earning per delivery
        earnings_per_delivery = 5.00
        
        # Step 1: Get current delivery stats
        response = supabase.table("driverdetails").select("total_deliveries, total_earnings").eq("driver_id", driver_id_str).execute()
        
        if not response.data:
            return jsonify(
                {
                    "code": 404,
                    "message": f"Driver with ID {driver_id_str} not found."
                }
            ), 404
            
        # Get current values
        current_stats = response.data[0]
        current_deliveries = current_stats.get("total_deliveries", 0)
        current_earnings = current_stats.get("total_earnings", 0.00)
        
        # Calculate new values
        new_deliveries = current_deliveries + 1
        new_earnings = float(current_earnings) + earnings_per_delivery
        
        # Step 2: Update the driver's stats
        update_data = {
            "total_deliveries": new_deliveries,
            "total_earnings": new_earnings
        }
        
        update_response = supabase.table("driverdetails").update(update_data).eq("driver_id", driver_id_str).execute()
        
        # Step 3: Return success response
        return jsonify(
            {
                "code": 200,
                "message": "Driver delivery stats updated successfully.",
                "data": {
                    "total_deliveries": new_deliveries,
                    "total_earnings": new_earnings
                }
            }
        ), 200

    except Exception as e:
        app.logger.error("Error updating driver delivery stats: %s", str(e), exc_info=True)
        return jsonify(
            {
                "code": 500,
                "message": "An internal server error occurred"
            }
        ), 500

# update live location directly using GPS coordinates from the browser (finally...)
@app.route("/api/driverdetails/<uuid:driver_id>/location", methods=['PATCH'])
def update_driver_location(driver_id):
    """
    Update driver's location directly using GPS coordinates from the browser
    """
    try:
        # Convert driver_id to string (required for Supabase queries)
        driver_id_str = str(driver_id)
        
        # Parse the request body
        data = request.json or {}
        location = data.get("location")
        accuracy = data.get("accuracy")
        
        if not location:
            return jsonify({
                "code": 400,
                "message": "Missing 'location' field in request body."
            }), 400
        
        # Update driver location in database
        update_response = supabase.table("driverdetails").update({
            "live_location": location
        }).eq("driver_id", driver_id_str).execute()
        
        # If record doesn't exist yet, automatically insert it (upsert)
        if not update_response.data:
            supabase.table("driverdetails").insert({
                "driver_id": driver_id_str,
                "live_location": location,
                "availability": True,
                "total_deliveries": 0,
                "total_earnings": 0.00
            }).execute()
        
        # Return success response
        return jsonify({
            "code": 200,
            "message": "Driver location updated successfully using device GPS.",
            "data": {
                "location": location,
                "accuracy": accuracy
            }
        }), 200
        
    except Exception as e:
        app.logger.error("Error updating driver location: %s", str(e), exc_info=True)
        return jsonify({
            "code": 500,
            "message": "An internal server error occurred"
        }), 500

# Main entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5012))
    print(f"Starting driver details service on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)