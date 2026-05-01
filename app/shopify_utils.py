import requests
import os
from datetime import datetime, timedelta

SHOPIFY_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
# We extract the domain dynamically or use a default
STORE_DOMAIN = "kyyhe6-ry.myshopify.com" 

def has_completed_order(email, phone):
    """
    Checks if there's a completed order for this email or phone 
    created in the last 60 minutes.
    """
    if not SHOPIFY_TOKEN:
        print("⚠️ Shopify token missing, skipping check (defaulting to No Order)")
        return False

    url = f"https://{STORE_DOMAIN}/admin/api/2023-10/orders.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }
    
    # We check orders from the last hour to be safe
    since_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    
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
                return order_name
            
            # Check phone match (normalizing to last 10 digits)
            order_phone = order.get("phone") or (order.get("customer") or {}).get("phone")
            if order_phone and phone:
                if phone[-10:] == str(order_phone)[-10:]:
                    return order_name
                    
        return None
    except Exception as e:
        print(f"💥 Shopify Check Exception: {e}")
        return False
