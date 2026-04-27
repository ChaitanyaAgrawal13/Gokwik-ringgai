import requests
import os
from dotenv import load_dotenv

load_dotenv()

import re

API_KEY = os.getenv("RINGG_API_KEY")
BASE_URL = os.getenv("RINGG_BASE_URL")
SHOPIFY_API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")

def extract_shopify_fabric(product_id, default_fabric):
    if not SHOPIFY_API_TOKEN or not product_id:
        return default_fabric
    url = f"https://kyyhe6-ry.myshopify.com/admin/api/2024-01/products/{product_id}.json"
    try:
        res = requests.get(url, headers={"X-Shopify-Access-Token": SHOPIFY_API_TOKEN}, timeout=5)
        if res.status_code == 200:
            html = res.json().get("product", {}).get("body_html", "")
            
            # Strip out all HTML tags (<p>, <span>) and replace them with newlines
            clean_text = re.sub(r'<[^>]+>', '\n', html)
            
            # Split into lines
            for line in clean_text.split('\n'):
                clean_line = line.strip()
                # Find the clean bullet point containing the fabric percentage
                if clean_line.startswith("-") and any(f in clean_line.lower() for f in ["cotton", "polyester", "linen", "satin", "silk", "spandex"]):
                    if len(clean_line) < 100:  # Prevent it from grabbing entire descriptive paragraphs
                        fabric_str = clean_line.lstrip("- ").strip()
                        # Remove GSM details to keep the voice prompt clean for the AI
                        fabric_str = re.sub(r'[,]?\s*\b\d+\s*GSM\b', '', fabric_str, flags=re.IGNORECASE).strip()
                        return fabric_str
                        
    except Exception:
        pass
    return default_fabric

def extract_shirt_details(title: str):
    """Dynamically extracts shirt details and creates a nice short spoken name."""
    if not title:
        return "your item", "Unknown", "100% Premium Cotton", "Regular Fit"
        
    t = title.lower()
    
    # 1. Extract Fabric
    fabric = "100% Premium Cotton"
    if "linen" in t: fabric = "Linen"
    elif "satin" in t: fabric = "Satin"
    elif "silk" in t: fabric = "Silk"
    elif "cotton" in t: fabric = "Cotton"
        
    # 2. Extract Color
    color = "Unknown"
    for c in ["blue", "brown", "grey", "gray", "black", "white", "red", "green", "pink", "yellow"]:
        if c in t:
            color = c.capitalize()
            break
            
    # 3. Extract Fit
    fit = "Regular Fit"
    if "slim" in t: fit = "Slim Fit"
    elif "loose" in t or "oversized" in t: fit = "Oversize Fit"
            
    # 4. Create Short Name (strip out sizing like "- M-40" and adjectives)
    ignore_words = {"pure", "italian", "luxe", "stretch", "regular", "fit", "premium", "slim"}
    base_title = title.split("-")[0].strip()
    
    simplified_words = []
    for w in base_title.split():
        if w.lower() not in ignore_words:
            simplified_words.append(w)
            
    short_name = " ".join(simplified_words)

    return short_name, color, fabric, fit

def get_preferred_language(state: str) -> str:
    """Decides the AI's spoken language based on the customer's state."""
    if not state:
        return "hindi"  # Default fallback
    s = state.lower().strip()
    
    # South Indian states defaults
    if s in ["karnataka", "kerala", "tamil nadu", "andhra pradesh", "telangana"]:
        return "english" # Or change to "kannada", "tamil" if Ringg supports it
        
    return "hindi"

def call_ringg_ai(user, agent_id="3f3a9cc0-2362-440e-a6c4-8de4a8d99979", from_number_id="3a75bd88-4872-4845-a580-2e9bec58961e"):
    # Official Ringg API Endpoint for outbound calls
    url = f"{BASE_URL}/ca/api/v0/calling/outbound/individual" 

    # Extract all the smart details from the raw title
    items = user.get("items", [])
    raw_title = items[0].get("title") if items else ""
    product_id = items[0].get("product_id") if items else None
    
    short_name, shirt_colour, shirt_fabric_fallback, shirt_fit = extract_shirt_details(raw_title)
    
    # Securely hit Shopify API to extract exactly what the true fabric percentage is
    shirt_fabric = extract_shopify_fabric(product_id, shirt_fabric_fallback)

    # Figure out the best language based on the buyer's location
    spoken_language = get_preferred_language(user.get("state", ""))

    phone = str(user["phone"])
    if not phone.startswith("+"):
        phone = f"+91{phone[-10:]}" # basic fallback for Indian numbers

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
            
            # Dynamically extracted variables
            "shirt_colour": shirt_colour,                
            "shirt_fabric": shirt_fabric,  
            "fit": shirt_fit,                  

            # You can also pass the recovery URL in case the prompt needs it!
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