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

# Find the first 10 uncalled records
users = collection.find({"called": False}).limit(10)
users_list = list(users)

if not users_list:
    print("❌ No uncalled checkouts found!")
else:
    print(f"✅ Found {len(users_list)} checkout(s). Executing test calls...\n")
    
    for user in users_list:
        print(f"🔄 Firing Ringg API Call for: {user.get('phone')} - {user.get('name')}")
        
        success, response = call_ringg_ai(user)
        
        print("--- 📞 RINGG AI API RAW RESPONSE ---")
        print(f"Status (HTTP 200 OK?): {success}")
        if isinstance(response, dict):
            print(json.dumps(response, indent=2))
        else:
            print(response)

        if success:
            collection.delete_one({"_id": user["_id"]})
            print(f"🗑️ Lead successfully called and removed from MongoDB.\n")
        else:
            print(f"❌ Call failed. Lead remains in MongoDB.\n")

print("✅ Finished processing the first 10 entries.")
