import os
import json
import feedparser
import requests
import re # <-- NEW IMPORT
from flask import Flask, jsonify, render_template, request
from twilio.rest import Client
from geopy.distance import geodesic # <-- NEW IMPORT

# Create the Flask web server
app = Flask(__name__)

# --- Configuration ---
# Load secret keys from Render's Environment Variables
TWILIO_ACCOUNT_SID = os.environ.get("AC4f1483a5fae4d92953da74268b18869e")
TWILIO_AUTH_TOKEN = os.environ.get("123f763563cc0a95d1a7c105450b48b8")
TWILIO_PHONE_NUMBER = os.environ.get("917339474485")

# This is the official NOAA/US Tsunami Warning Center Feed
TSUNAMI_FEED_URL = "https.www.tsunami.gov/events/xml/PAAQAtom.xml"

# --- OneSignal Configuration (if you use it) ---
ONESIGNAL_APP_ID = os.environ.get("c12adc07-b70b-4765-be23-4fb9d7c4cc95")
ONESIGNAL_API_KEY = os.environ.get("os_v2_app_yevnyb5xbndwlprdj645prgmsvrlrrxqb74ewrnkjd3tkhru3wibftdnz66ofznzbznni3icsroxf7muih2uashsptbaj3mpqlfrhoa")


# --- UPDATED: Twilio SMS Function ---
# This function now sends an alert to a SPECIFIC user
def send_sms_to_user(user_phone, title, summary):
    """Sends an SMS to a specific user using Twilio"""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("Twilio env vars not set. Cannot send SMS.")
        return
        
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message_body = f"URGENT ALERT (Near You):\n{title}\n\n{summary}"
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=user_phone 
        )
        print(f"Successfully sent SMS to {user_phone}")
    except Exception as e:
        print(f"Error sending SMS to {user_phone}: {e}")

# --- OneSignal Push Function (Unchanged) ---
def send_push_notification(title, message):
    if not ONESIGNAL_APP_ID or not ONESIGNAL_API_KEY:
        print("OneSignal is not configured. Skipping push notification.")
        return
    
    print("Sending push notification...")
    headers = {
        "accept": "application/json",
        "Authorization": f"Basic {ONESIGNAL_API_KEY}",
        "content-type": "application/json"
    }
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["Subscribed Users"],
        "headings": {"en": title},
        "contents": {"en": message}
    }
    try:
        response = requests.post(
            "https.api.onesignal.com/api/v1/notifications",
            headers=headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        print(f"Push notification sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending push notification: {e}")


# --- UPDATED: Background Disaster Check ---
def check_for_new_disaster():
    """
    Checks feed, gets disaster location, and finds users nearby.
    """
    print("Checking for disaster alerts...")
    feed = feedparser.parse(TSUNAMI_FEED_URL)
    if not feed.entries:
        print("Feed is empty.")
        return

    latest_alert = feed.entries[0]
    alert_title = latest_alert.title
    alert_summary = latest_alert.summary

    # --- 1. Find the disaster's location (Lat/Lon) ---
    # We will use Regex to find "Lat/Lon: 12.345 / -123.456" in the summary
    location_match = re.search(r"Lat/Lon:\s*(-?\d+\.\d+)\s*/\s*(-?\d+\.\d+)", alert_summary)
    
    if not location_match:
        print(f"Could not find Lat/Lon for alert: {alert_title}")
        return # Can't analyze without a location

    disaster_lat = float(location_match.group(1))
    disaster_lon = float(location_match.group(2))
    disaster_location = (disaster_lat, disaster_lon)
    print(f"Disaster location found: {disaster_location}")

    # --- 2. Get all users from your database ---
    #
    # --- !! CRITICAL DATABASE STEP !! ---
    #
    # This is where you MUST fetch all users from your database.
    # Example DB command:
    # all_users = db.execute("SELECT phone, latitude, longitude FROM users")
    #
    # For this demo, I will use a FAKE list.
    #
    print("Fetching users (DEMO LIST)...")
    all_users = [
        # This first user is your test number, but with a FAKE location
        {"phone": os.environ.get("USER_PHONE_NUMBER"), "latitude": 66.500, "longitude": -162.500}, # Fake location near disaster
        {"phone": os.environ.get("USER_PHONE_NUMBER"), "latitude": 40.7128, "longitude": -74.0060}  # Fake New York location
    ]

    # --- 3. Analyze: Find users in the danger zone ---
    
    # How many miles counts as "nearby"?
    DANGER_ZONE_MILES = 500 

    for user in all_users:
        if not user.get("phone"):
            continue
            
        user_location = (user["latitude"], user["longitude"])
        
        # Calculate distance
        distance = geodesic(user_location, disaster_location).miles
        
        print(f"Checking user {user['phone']}. Distance: {distance:.2f} miles.")

        if distance <= DANGER_ZONE_MILES:
            print(f"!!! ALERTING USER: {user['phone']} is IN danger zone! !!!")
            
            # Send the SMS *to this specific user*
            send_sms_to_user(user["phone"], alert_title, alert_summary)
        else:
            print(f"User {user['phone']} is safe.")
            
            
# --- Website Page (For the User) ---
@app.route("/")
def index():
    return render_template("index.html")

# --- API Endpoint (For the Frontend) ---
@app.route("/api/get-latest-alert")
def get_latest_alert():
    # (This function is unchanged from our last version)
    feed = feedparser.parse(TSUNAMI_FEED_URL)
    
    if not feed.entries:
        return jsonify({"title": "No Alerts Active", "summary": "...", "link": "#", "count": 0})
    
    latest_alert = feed.entries[0]
    total_alerts = len(feed.entries)
    
    return jsonify({
        "title": latest_alert.title,
        "summary": latest_alert.summary,
        "link": latest_alert.link,
        "count": total_alerts
    })

# --- UPDATED API ENDPOINT (For Subscribing) ---
@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    """
    Receives a phone number AND location from the frontend.
    """
    data = request.get_json()
    phone_number = data.get('phone')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not phone_number or not latitude or not longitude:
        return jsonify({"message": "Error: Phone, lat, and lon are required."}), 400

    #
    # --- !! CRITICAL DATABASE STEP !! ---
    #
    # This is where you MUST save the data to your database.
    # Without this, the server forgets the user immediately.
    #
    # Example DB command:
    # db.execute("INSERT INTO users (phone, latitude, longitude) VALUES (?, ?, ?)",
    #            phone_number, latitude, longitude)
    #
    print(f"!!! NEW SUBSCRIBER: {phone_number} at ({latitude}, {longitude}) !!!")
    print("!!! (Remember: This is not saved to a database yet) !!!")

    return jsonify({"message": "Subscribed successfully!"})
