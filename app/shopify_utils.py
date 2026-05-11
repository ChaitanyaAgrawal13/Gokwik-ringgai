import requests
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# We extract the domain dynamically or use a default
STORE_DOMAIN = "kyyhe6-ry.myshopify.com" 

def has_completed_order(email, phone, since_time):
    """
    Checks if there's a completed order for this email or phone 
    created since the abandonment time.
    """
    shopify_token = os.getenv("SHOPIFY_API_TOKEN")
    if not shopify_token:
        print("⚠️ Shopify token missing, skipping check (defaulting to No Order)")
        return None

    url = f"https://{STORE_DOMAIN}/admin/api/2024-01/orders.json"
    headers = {
        "X-Shopify-Access-Token": shopify_token,
        "Content-Type": "application/json"
    }
    
    # Use the provided abandonment time (must be ISO string)
    params = {
        "status": "any",
        "created_at_min": since_time,
        "limit": 50
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ Shopify API Error: {response.status_code} - {response.text}")
            return False
            
        orders = response.json().get("orders", [])
        
        for order in orders:
            order_name = order.get("name", "Unknown ID")
            # Check email match
            if email and order.get("email") == email:
                return {"name": order_name, "created_at": order.get("created_at")}
            
            # Check phone match (normalizing to last 10 digits)
            order_phones = [
                order.get("phone"),
                (order.get("customer") or {}).get("phone"),
                (order.get("shipping_address") or {}).get("phone"),
                (order.get("billing_address") or {}).get("phone")
            ]
            
            # Remove None values and normalize to last 10 digits
            order_phones = [str(p)[-10:] for p in order_phones if p]
            
            if phone and phone[-10:] in order_phones:
                return {"name": order_name, "created_at": order.get("created_at")}
                    
        return None
    except Exception as e:
        print(f"💥 Shopify Check Exception: {e}")
        return False
