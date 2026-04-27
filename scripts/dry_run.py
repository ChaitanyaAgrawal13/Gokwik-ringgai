import json
from dotenv import load_dotenv

load_dotenv()

from app.models import create_checkout
from app.ringg import extract_shirt_details, extract_shopify_fabric, get_preferred_language

p1 = {
  "total_price": "999.0000",
  "items": [{"title": "Slim Fit Sand Beige Knit Shirt - XS-36", "product_id": 9370564952308, "price": 99900, "quantity": 1}],
  "address": {"city": "NEW DELHI", "state": "DELHI", "phone": "9568055566"},
  "customer": {"firstname": "Jayant", "lastname": "Jayant"}
}

p2 = {
  "total_price": "2499.0000",
  "items": [{"title": "Ice Blue Pure Italian Linen Shirt - XL-44", "product_id": 9411365110004, "price": 249900, "quantity": 1}],
  "address": {"city": "JABALPUR", "state": "MADHYA PRADESH", "phone": "9893407889"},
  "customer": {"firstname": "Manish", "lastname": "Sharma"}
}

for i, p in enumerate([p1, p2]):
    print(f"\n{'='*50}\nTESTING PAYLOAD #{i+1}\n{'='*50}")
    
    # 1. Simulate the webhook hitting models.py
    user = create_checkout(p)
    items = user.get("items", [])
    raw_title = items[0].get("title") if items else ""
    
    # Notice we need to pull product_id from the original payload because create_checkout 
    # currently doesn't preserve product_id in its items list! 
    # Wait, let's fix that too later if it's missing. For this test, we pull from the raw payload
    product_id = p["items"][0].get("product_id")
    
    # 2. Simulate the python extraction logic
    short_name, shirt_colour, fabric_fallback, shirt_fit = extract_shirt_details(raw_title)
    
    # 3. Simulate hitting the live Shopify API regex!
    true_fabric = extract_shopify_fabric(product_id, fabric_fallback)
    
    # 4. Simulate State Language Mapping
    language = get_preferred_language(user.get("state", ""))
    
    print(f"🧑 Customer: {user.get('name')} ({user.get('phone')})")
    print(f"📍 Location: {user.get('city')}, {user.get('state')} -> 🗣️ Routed Language: {language.upper()}")
    print("-" * 30)
    print(f"📦 Original Title: {raw_title}")
    print(f"✂️ Spoken Name: {short_name}")
    print(f"👕 Fit: {shirt_fit}")
    print(f"🎨 Colour: {shirt_colour}")
    print(f"🧵 Fabric: {true_fabric}")
    print("-" * 30)
