import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient

# Must load dotenv before importing ringg to ensure API keys are populated
load_dotenv()

from app.ringg import call_ringg_ai

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

print("🔍 Hooking into MongoDB...")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["checkouts"]

# Find the NEWEST record that hasn't been called yet
user = collection.find_one({"called": False}, sort=[("_id", -1)])

if not user:
    print("❌ No uncalled checkouts found!")
else:
    print(f"✅ Found checkout for: {user.get('phone')} - {user.get('name')}")
    print("🚀 Firing Ringg API Call (this will use your APP variables)...\n")
    
    success, response = call_ringg_ai(user)
    
    print("--- 📞 RINGG AI API RAW RESPONSE ---")
    print(f"Status (HTTP 200 OK?): {success}")
    if isinstance(response, dict):
        print(json.dumps(response, indent=2))
    else:
        print(response)
