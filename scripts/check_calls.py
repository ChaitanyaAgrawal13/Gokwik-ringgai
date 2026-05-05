import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import collection

load_dotenv()

def check_call_outcomes():
    print("📞 RECENT CALL OUTCOMES (Last 24 Hours):")
    print("-" * 60)
    
    yesterday = datetime.utcnow() - timedelta(hours=24)
    calls = list(collection.find({
        "status": {"$in": ["called", "whatsapp_sent", "whatsapp_failed"]},
        "created_at": {"$gt": yesterday}
    }).sort("created_at", -1))
    
    if not calls:
        print("No calls found in the last 24 hours.")
        return

    for doc in calls:
        name = doc.get("name", "Unknown")
        phone = doc.get("phone", "Unknown")
        status = doc.get("status", "Unknown")
        analysis = doc.get("call_analysis", {})
        asked = analysis.get("whatsapp_message_asked", "N/A")
        duration = doc.get("call_duration", 0)
        
        print(f"👤 {name} ({phone})")
        print(f"   📍 Status: {status}")
        print(f"   ⏱️ Duration: {duration}s")
        print(f"   📱 Asked for WhatsApp: {asked}")
        if status == "whatsapp_sent":
            print(f"   🆔 Msg ID: {doc.get('whatsapp_message_id')}")
            print(f"   📊 Delivery: {doc.get('whatsapp_delivery_status', 'Pending')}")
        print("-" * 30)

if __name__ == "__main__":
    check_call_outcomes()
