from flask import Flask, jsonify, render_template
import feedparser  # This library fetches and parses the alert feed
from twilio.rest import Client # This is for sending SMS

# --- Configuration ---
# Your Account SID and Auth Token from twilio.com/console
# DO NOT put your real keys here if you share this code.
TWILIO_ACCOUNT_SID = "AC4f1483a5fae4d92953da74268b18869e"  # <-- PUT YOUR KEY HERE
TWILIO_AUTH_TOKEN = "123f763563cc0a95d1a7c105450b48b8"    # <-- PUT YOUR KEY HERE
TWILIO_PHONE_NUMBER = "+917339474485"        # <-- Your Twilio number
USER_PHONE_NUMBER = "+917339474485"            # <-- The user's number to alert

# This is the official NOAA/US Tsunami Warning Center Feed
TSUNAMI_FEED_URL = "https://www.tsunami.gov/events/xml/PAAQAtom.xml"

# Create the Flask web server
app = Flask(__name__)

# --- Background "AI" Logic (Simplified) ---
# In a real app, this would run on a separate schedule, not just on server start
def check_for_new_disaster():
    """
    Checks the feed for new alerts.
    This is a FAKE "AI" and "rule engine".
    A real app would store alerts in a database to see which ones are "new".
    """
    print("Checking for disaster alerts...")
    feed = feedparser.parse(TSUNAMI_FEED_URL)
    
    if not feed.entries:
        print("Feed is empty, no alerts found.")
        return

    # Get the very latest alert from the feed
    latest_alert = feed.entries[0]
    alert_title = latest_alert.title
    
    # SIMPLE RULE ENGINE:
    # If the title contains "Warning" or "Watch", we treat it as serious.
    if "Warning" in alert_title or "Watch" in alert_title:
        print(f"!!! SERIOUS ALERT DETECTED: {alert_title}")
        
        # --- SEND THE SMS ALERT ---
        # We only send the alert if the keys are not the default ones
        if "YOUR_ACCOUNT_SID_HERE" not in TWILIO_ACCOUNT_SID:
            send_sms_alert(alert_title, latest_alert.summary)
        else:
            print("Twilio is not configured. Skipping SMS.")
    else:
        print(f"Informational alert found: {alert_title}")

def send_sms_alert(title, summary):
    """Sends an SMS using Twilio"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message_body = f"URGENT DISASTER ALERT:\n{title}\n\n{summary}"
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=USER_PHONE_NUMBER
        )
        print(f"Successfully sent SMS with SID: {message.sid}")
    except Exception as e:
        print(f"Error sending SMS: {e}")
        print("Please check your Twilio SID, Token, and Phone Numbers.")


# --- API Endpoint (For the Frontend) ---
@app.route("/api/get-latest-alert")
def get_latest_alert():
    """
    This is an API endpoint.
    The frontend will call this URL to get data.
    """
    feed = feedparser.parse(TSUNAMI_FEED_URL)
    
    if not feed.entries:
        return jsonify({"title": "No Alerts Active", "summary": "No current alerts from the feed."})
    
    # Get the latest entry
    latest_alert = feed.entries[0]
    
    # Return the data as JSON
    return jsonify({
        "title": latest_alert.title,
        "summary": latest_alert.summary,
        "link": latest_alert.link
    })


# --- Website Page (For the User) ---
@app.route("/")
def index():
    """
    This is the main webpage.
    It just serves the 'index.html' file.
    """
    return render_template("index.html")


# --- Run the App ---
if __name__ == "__main__":
    # 1. Check for disasters once when the server starts
    check_for_new_disaster()
    
    # 2. Start the web server to answer requests
    # debug=True reloads the server when you change code
    app.run(debug=True)
