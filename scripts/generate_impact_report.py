import os
import sys
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import collection

load_dotenv()

SHOPIFY_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
STORE_DOMAIN = "kyyhe6-ry.myshopify.com"

def fetch_shopify_orders(days=9):
    """Fetch all orders from Shopify for the last N days."""
    since_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
    url = f"https://{STORE_DOMAIN}/admin/api/2023-10/orders.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    params = {"status": "any", "created_at_min": since_time, "limit": 250}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            return response.json().get("orders", [])
        print(f"❌ Shopify Error: {response.status_code}")
        return []
    except Exception as e:
        print(f"💥 Exception fetching orders: {e}")
        return []

def normalize_phone(phone):
    if not phone: return ""
    return "".join(filter(str.isdigit, str(phone)))[-10:]

def generate_report():
    print("🔍 Fetching data for the last 6 days...")
    
    # 1. Get all customers called in the last 6 days
    since_call = datetime.utcnow() - timedelta(days=6)
    # Search for anything that has a last_called_at timestamp OR whatsapp_sent_at
    called_customers = list(collection.find({
        "$or": [
            {"last_called_at": {"$gte": since_call}},
            {"whatsapp_sent_at": {"$gte": since_call}}
        ]
    }))
    
    if not called_customers:
        print("No calls found in the last 6 days.")
        return

    # 2. Fetch recent Shopify orders
    all_orders = fetch_shopify_orders(days=9)
    
    print(f"✅ Found {len(called_customers)} customers called.")
    print(f"✅ Fetched {len(all_orders)} recent Shopify orders.")
    print("-" * 60)
    
    conversions = []
    
    for cust in called_customers:
        cust_phone = normalize_phone(cust.get("phone"))
        cust_email = cust.get("email", "").lower().strip()
        call_time = cust.get("last_called_at")
        
        # Find orders for this customer
        matching_orders = []
        for order in all_orders:
            order_time = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            
            # Match by phone or email
            order_phones = [
                normalize_phone(order.get("phone")),
                normalize_phone((order.get("customer") or {}).get("phone")),
                normalize_phone((order.get("shipping_address") or {}).get("phone"))
            ]
            order_email = (order.get("email") or "").lower().strip()
            
            is_match = (cust_phone and cust_phone in order_phones) or (cust_email and cust_email == order_email)
            
            # Check if order was placed AFTER the call
            if is_match and order_time > call_time:
                matching_orders.append(order)
        
        if matching_orders:
            conversions.append({
                "customer": cust.get("name", "Unknown"),
                "phone": cust.get("phone"),
                "called_at": call_time,
                "orders": matching_orders
            })

    # 3. Print Report
    print(f"\n📈 RINGG AI CONVERSION IMPACT REPORT (Last 6 Days)")
    print("=" * 60)
    
    if not conversions:
        print("No conversions found after calls in this period.")
    else:
        for conv in conversions:
            print(f"👤 Customer: {conv['customer']} ({conv['phone']})")
            print(f"   📞 Called At: {conv['called_at'].strftime('%Y-%m-%d %H:%M')}")
            
            for i, order in enumerate(conv['orders'], 1):
                order_time = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).strftime('%Y-%m-%d %H:%M')
                items = ", ".join([item['title'] for item in order.get('line_items', [])])
                print(f"   🛒 Order #{i}: {order['name']} on {order_time}")
                print(f"      Items: {items}")
                print(f"      Value: {order.get('total_price')} {order.get('currency')}")
            print("-" * 40)
            
    print(f"\n📊 Summary: {len(conversions)} customers converted after receiving a call.")

if __name__ == "__main__":
    generate_report()
