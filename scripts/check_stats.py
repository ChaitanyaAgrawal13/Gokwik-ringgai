import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import collection

load_dotenv()

def check_latest_stats():
    print("📊 LATEST CUSTOMER STATUS DUMP:")
    print("-" * 50)
    
    # Get latest 10 records
    latest = list(collection.find().sort("created_at", -1).limit(10))
    
    if not latest:
        print("No records found in database.")
        return

    for doc in latest:
        name = doc.get("name", "Unknown")
        phone = doc.get("phone", "Unknown")
        status = doc.get("status", "Unknown")
        wa_status = doc.get("whatsapp_delivery_status", "N/A")
        wa_delivered = doc.get("whatsapp_delivered", False)
        msg_id = doc.get("whatsapp_message_id", "None")
        converted = doc.get("converted", False)
        
        print(f"👤 {name} ({phone})")
        print(f"   📍 Status: {status}")
        print(f"   🆔 Msg ID: {msg_id}")
        print(f"   📱 WA Delivery: {wa_status} (Delivered: {wa_delivered})")
        print(f"   💰 Converted: {converted}")
        print("-" * 20)

if __name__ == "__main__":
    check_latest_stats()
