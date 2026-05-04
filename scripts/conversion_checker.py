import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import collection
from app.shopify_utils import has_completed_order

load_dotenv()

def check_for_conversions():
    """
    Checks for conversions and attributes them to either the Call or WhatsApp.
    """
    print(f"🕒 Starting Attribution-Aware Conversion Check at {datetime.utcnow()}...")
    
    # 1. Check customers who were CALLED but didn't get/ask for WhatsApp yet
    query_call = {
        "status": "called",
        "converted": False,
        "last_called_at": {"$gte": datetime.utcnow() - timedelta(days=2)}
    }
    
    # 2. Check customers who were sent WHATSAPP
    query_wa = {
        "status": "whatsapp_sent",
        "converted": False,
        "whatsapp_sent_at": {"$gte": datetime.utcnow() - timedelta(days=2)}
    }
    
    for category, query in [("Call-Only", query_call), ("WhatsApp", query_wa)]:
        customers = list(collection.find(query))
        print(f"🔎 Checking {len(customers)} customers in {category} category...")

        for customer in customers:
            phone = customer.get("phone")
            email = customer.get("email")
            
            # Use the most recent interaction time as the baseline
            since_time = (customer.get("whatsapp_sent_at") or customer.get("last_called_at")).isoformat()
            
            order_name = has_completed_order(email, phone, since_time)
            
            if order_name:
                print(f"  ✅ {category} CONVERSION! Order {order_name} for {phone}")
                collection.update_one(
                    {"_id": customer["_id"]},
                    {"$set": {
                        "status": "converted",
                        "converted": True,
                        "attribution": category.lower(),
                        "order_id": order_name,
                        "converted_at": datetime.utcnow()
                    }}
                )

    print(f"🏁 Check complete.")

if __name__ == "__main__":
    check_for_conversions()
