import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import collection

load_dotenv()

def analyze_failures():
    # Last 24 hours
    since = datetime.utcnow() - timedelta(hours=24)
    
    total = collection.count_documents({"created_at": {"$gte": since}})
    whatsapp_sent = collection.count_documents({
        "created_at": {"$gte": since},
        "whatsapp_sent": True
    })
    whatsapp_failed = collection.count_documents({
        "created_at": {"$gte": since},
        "status": "whatsapp_failed"
    })
    
    # Analyze error reasons
    pipeline = [
        {"$match": {
            "created_at": {"$gte": since},
            "status": "whatsapp_failed"
        }},
        {"$group": {
            "_id": "$last_error",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    error_reasons = list(collection.aggregate(pipeline))
    
    print(f"📊 ANALYSIS FOR LAST 24 HOURS (Since {since})")
    print(f"Total Checkouts: {total}")
    print(f"WhatsApp Sent: {whatsapp_sent}")
    print(f"WhatsApp Failed: {whatsapp_failed}")
    
    print("\n❌ Failure Reasons:")
    for err in error_reasons:
        print(f" - {err['_id']}: {err['count']}")

if __name__ == "__main__":
    analyze_failures()
