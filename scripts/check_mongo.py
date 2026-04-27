import os
from pprint import pprint
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

print("Checking MongoDB Records...")

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["checkouts"]

    count = collection.count_documents({})
    print(f"\nTotal Webhook checkouts stored in DB: {count}")

    # Fetch the 2 most recent records
    latest_records = list(collection.find().sort("_id", -1).limit(2))
    
    if latest_records:
        print("\n--- Latest Records ---")
        for idx, record in enumerate(latest_records, 1):
            print(f"\nRecord #{idx}:")
            print(f"  Phone: {record.get('phone')}")
            print(f"  Name: {record.get('name')}")
            print(f"  City/State: {record.get('city')}, {record.get('state')}")
            print(f"  Cart Value: {record.get('cart_value')}")
            
            items = record.get('items', [])
            print(f"  Items in Cart: {len(items)}")
            for item in items:
                print(f"    - {item.get('title')} (Qty: {item.get('quantity')})")
                
            print(f"  Recovery URL: {record.get('recovery_url')}")
            print(f"  Created At: {record.get('created_at')}")
    else:
        print("\nNo records found in the database yet.")

except Exception as e:
    print(f"\n❌ Error connecting to MongoDB: {e}")
