from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client
import requests
import os

app = Flask(__name__)

# 🔐 YOUR SECRET KEYS - REPLACE THESE!
SUPABASE_URL = "https://YOUR-PROJECT-ID.supabase.co"  # From Step 4C
SUPABASE_KEY = "YOUR-SUPABASE-KEY"  # From Step 4C
WEATHER_API_KEY = "YOUR-WEATHER-API-KEY"  # From Step 5

# Connect to database
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_weather_advice(district):
    """Magic weather function using REAL API"""
    try:
        # Convert Indian districts to cities OpenWeatherMap understands
        district_map = {
            "YAV": "Yavatmal", 
            "PUN": "Pune",
            "NAS": "Nashik",
            "AKO": "Akola"
        }
        
        city = district_map.get(district, "Pune")  # Default to Pune
        
        # REAL API CALL!
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            weather_desc = data['weather'][0]['description']
            
            # Smart advice based on weather
            if "rain" in weather_desc.lower():
                advice = "🌧 Rain expected! Delay pesticide spraying."
            elif temp > 35:
                advice = "🔥 Hot day! Water crops in early morning."
            else:
                advice = "🌤 Good weather for field work."
                
            return f"Weather in {city}: {temp}°C, {humidity}% humidity. {advice}"
        else:
            return "Weather service busy. Check local forecast."
            
    except Exception as e:
        return "Weather data unavailable. Contact local agriculture office."

@app.route('/sms', methods=['POST'])
def sms_reply():
    # Get farmer's message and number
    incoming_msg = request.values.get('Body', '').strip().lower()
    farmer_number = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    # 🗄 CHECK DATABASE: See if farmer exists
    response = supabase.table("farmers").select("*").eq("phone_number", farmer_number).execute()
    existing_farmer = response.data

    # 🎯 HANDLE DIFFERENT COMMANDS
    if incoming_msg.startswith('reg'):
        # Example: "REG YAV Cotton"
        parts = incoming_msg.split(' ')
        if len(parts) >= 3:
            district = parts[1].upper()
            crop = parts[2].title()
            
            # 🗄 SAVE TO DATABASE!
            if existing_farmer:
                # Update existing farmer
                data = supabase.table("farmers").update({
                    "district": district, 
                    "crop": crop
                }).eq("phone_number", farmer_number).execute()
            else:
                # Create new farmer
                data = supabase.table("farmers").insert({
                    "phone_number": farmer_number,
                    "district": district, 
                    "crop": crop
                }).execute()
            
            reply_text = f"✅ Registered! {crop} in {district}. Text PEST, FERT, or WEATHER."
        else:
            reply_text = "❌ Format: REG DISTRICT CROP (e.g., REG YAV Cotton)"

    elif 'pest' in incoming_msg:
        if existing_farmer:
            farmer_data = existing_farmer[0]
            crop = farmer_data["crop"]
            district = farmer_data["district"]
            
            # Smart pest advice
            if crop.lower() == "cotton" and district == "YAV":
                reply_text = "⚠ Cotton in Yavatmal: Watch for Aphids. Use neem oil spray."
            elif crop.lower() == "rice" and district == "PUN":
                reply_text = "⚠ Rice in Pune: Leaf Folder detected. Use recommended pesticides."
            else:
                reply_text = f"⚠ For {crop} in {district}: Monitor daily, consult local experts."
        else:
            reply_text = "❌ Please register first: REG DISTRICT CROP"

    elif 'fert' in incoming_msg:
        if existing_farmer:
            farmer_data = existing_farmer[0]
            crop = farmer_data["crop"]
            reply_text = f"🌱 For {crop}: Use DAP (50kg/acre). Test soil first."
        else:
            reply_text = "❌ Please register first."

    elif 'weather' in incoming_msg:
        if existing_farmer:
            farmer_data = existing_farmer[0]
            district = farmer_data["district"]
            # 🌤 REAL API CALL!
            reply_text = get_weather_advice(district)
        else:
            reply_text = "❌ Please register first."

    else:
        reply_text = "👋 Hi Farmer! Text: REG DISTRICT CROP to start (e.g., REG YAV Cotton)"

    msg.body(reply_text)
    return str(resp)

if __name__ == '__main__':
    app.run(debug=True)
