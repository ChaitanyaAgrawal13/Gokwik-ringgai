import requests
import os
from dotenv import load_dotenv

load_dotenv()

import re

API_KEY = os.getenv("RINGG_API_KEY")
BASE_URL = os.getenv("RINGG_BASE_URL")
SHOPIFY_API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")

def fetch_shopify_product_data(product_id):
    """Fetches product details and metafields from Shopify."""
    if not SHOPIFY_API_TOKEN or not product_id:
        return None, []
    
    headers = {"X-Shopify-Access-Token": SHOPIFY_API_TOKEN}
    product_url = f"https://kyyhe6-ry.myshopify.com/admin/api/2024-01/products/{product_id}.json"
    metafields_url = f"https://kyyhe6-ry.myshopify.com/admin/api/2024-01/products/{product_id}/metafields.json"
    
    product_data = None
    metafields = []
    
    try:
        p_res = requests.get(product_url, headers=headers, timeout=5)
        if p_res.status_code == 200:
            product_data = p_res.json().get("product")
            
        m_res = requests.get(metafields_url, headers=headers, timeout=5)
        if m_res.status_code == 200:
            metafields = m_res.json().get("metafields", [])
    except Exception as e:
        print(f"Shopify API error: {e}")
        
    return product_data, metafields

def extract_shirt_details(title: str, body_html: str = "", metafields: list = []):
    """Dynamically extracts shirt details using Shopify data and subtractive title parsing."""
    if not title:
        return "your item", "Unknown", "100% Premium Cotton", "Regular Fit"
    
    # Initialize defaults
    fabric = "100% Premium Cotton"
    fit = "Regular Fit"
    color = "Unknown"
    
    # 1. Look for explicit values in Metafields first
    product_ab_title = ""
    for m in metafields:
        if m['namespace'] == 'custom' and m['key'] == 'fit':
            fit = m['value']
        if m['namespace'] == 'custom' and m['key'] == 'product_ab_title':
            product_ab_title = m['value']

    # 2. Extract Fabric from Body HTML (Primary Source)
    if body_html:
        clean_text = re.sub(r'<[^>]+>', '\n', body_html)
        for line in clean_text.split('\n'):
            clean_line = line.strip()
            if clean_line.startswith("-") and any(f in clean_line.lower() for f in ["cotton", "polyester", "linen", "satin", "silk", "spandex", "viscose", "tencel", "lyocell"]):
                if len(clean_line) < 100:
                    fabric_str = clean_line.lstrip("- ").strip()
                    fabric = re.sub(r'[,]?\s*\b\d+\s*GSM\b', '', fabric_str, flags=re.IGNORECASE).strip()
                    break

    # 3. If Fabric is still default, try title guessing
    t = title.lower()
    if fabric == "100% Premium Cotton":
        if "linen" in t: fabric = "Linen"
        elif "satin" in t: fabric = "Satin"
        elif "silk" in t: fabric = "Silk"
        elif "knit" in t: fabric = "Knit"
        elif "tencel" in t: fabric = "Tencel"

    # 4. If Fit is still default, try title guessing
    if fit == "Regular Fit":
        if "slim" in t: fit = "Slim Fit"
        elif "loose" in t or "oversized" in t: fit = "Oversize Fit"

    # 5. Extract Color using "Subtractive" Logic
    # Use product_ab_title if available as it's usually cleaner
    base_name = product_ab_title if product_ab_title else title.split("-")[0].strip()
    
    # Words to subtract
    subtract_keywords = {
        "pure", "italian", "luxe", "stretch", "regular", "fit", "premium", "slim", 
        "shirt", "pant", "kurta", "knitted", "knit", "textured", "satin", "linen", 
        "cotton", "solid", "printed", "print", "blend", "lycra", "solid", "shirt",
        "sand", "viscose", "nylon", "spandex", "crinkle", "texture", "relaxed",
        "oversize", "oversized", "dobby", "twill", "oxford", "tencel", "lyocell",
        "tencel™", "lyocell™"
    }
    
    color_words = []
    for word in base_name.split():
        clean_word = word.strip(",.()").lower()
        if clean_word not in subtract_keywords:
            color_words.append(word)
    
    if color_words:
        color = " ".join(color_words)
        
    # Pass the unfiltered original title as the spoken name
    short_name = title

    return short_name, color, fabric, fit

def get_preferred_language(state: str) -> str:
    """Decides the AI's spoken language based on the customer's state."""
    if not state:
        return "hindi"
    s = state.lower().strip()
    if s in ["karnataka", "kerala", "tamil nadu", "andhra pradesh", "telangana"]:
        return "english"
    return "hindi"

def call_ringg_ai(user, agent_id="3f3a9cc0-2362-440e-a6c4-8de4a8d99979", from_number_id="3a75bd88-4872-4845-a580-2e9bec58961e"):
    url = f"{BASE_URL}/ca/api/v0/calling/outbound/individual" 

    items = user.get("items", [])
    raw_title = items[0].get("title") if items else ""
    product_id = items[0].get("product_id") if items else None
    
    # Fetch real-time data from Shopify
    product_data, metafields = fetch_shopify_product_data(product_id)
    body_html = product_data.get("body_html", "") if product_data else ""
    
    # Smarter detail extraction
    short_name, shirt_colour, shirt_fabric, shirt_fit = extract_shirt_details(raw_title, body_html, metafields)

    spoken_language = get_preferred_language(user.get("state", ""))

    phone = str(user["phone"])
    if not phone.startswith("+"):
        phone = f"+91{phone[-10:]}"

    payload = {
        "name": user.get("name", "Customer"),
        "mobile_number": phone,
        "agent_id": agent_id,              
        "from_number_id": from_number_id,  
        "custom_args_values": {            
            "callee_name": user.get("name", "Customer"),
            "original_callee_name": user.get("name", "Customer"),
            "shirt_name": short_name,
            "shirt_price": str(user.get("cart_value")),
            "language": spoken_language,
            "mobile_number": phone,
            "shirt_colour": shirt_colour,                
            "shirt_fabric": shirt_fabric,  
            "fit": shirt_fit,                  
            "recovery_url": user.get("recovery_url", "")
        }
    }

    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)