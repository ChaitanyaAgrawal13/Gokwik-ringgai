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

# Trailing size suffix on product titles, e.g. "M-40", "XXL-46", "L", "Medium-40".
_SIZE_SUFFIX = re.compile(
    r"^(?:XS|XXXL|XXL|XL|3XL|2XL|S|M|L|SMALL|MEDIUM|LARGE|\d{2})"
    r"(?:[-/ ]?\d{1,3})?$",
    re.IGNORECASE,
)


def strip_size_from_title(title: str) -> str:
    """Removes a trailing size suffix from a product title so the voice agent
    says just the shirt name, not the size.

    e.g. 'Slim Fit Sand Beige Knit Shirt - M-40' -> 'Slim Fit Sand Beige Knit Shirt'

    A trailing segment is dropped only when it actually looks like a size, so a
    real product name that happens to contain ' - ' is left untouched.
    """
    if not title or " - " not in title:
        return title
    base, last = title.rsplit(" - ", 1)
    if _SIZE_SUFFIX.match(last.strip()):
        return base.strip()
    return title.strip()


def _variant_available(variant: dict) -> bool:
    """Whether a single Shopify variant can currently be ordered."""
    if not variant.get("inventory_management"):
        return True  # Shopify is not tracking stock for this variant
    if variant.get("inventory_policy") == "continue":
        return True  # overselling is allowed
    return (variant.get("inventory_quantity") or 0) > 0


def get_stock_status(product_data: dict, raw_title: str) -> str:
    """Returns 'yes' or 'no' for whether the customer's size is in stock.

    The Shopify variant id (option1 / title) matches the size suffix of the
    cart title, e.g. 'M-40'. Defaults to 'yes' whenever stock cannot be
    determined, so a data gap never blocks a sale.
    """
    if not product_data:
        return "yes"
    variants = product_data.get("variants") or []
    if not variants:
        return "yes"

    size = ""
    if raw_title and " - " in raw_title:
        last = raw_title.rsplit(" - ", 1)[1].strip()
        if _SIZE_SUFFIX.match(last):
            size = last

    def norm(value):
        return re.sub(r"[^a-z0-9]", "", str(value or "").lower())

    nsize = norm(size)
    if nsize:
        for v in variants:
            if nsize in (norm(v.get("option1")), norm(v.get("title"))):
                return "yes" if _variant_available(v) else "no"

    # Size not matched (or not present) — in stock if any variant is available.
    return "yes" if any(_variant_available(v) for v in variants) else "no"

# --- Customer name handling -------------------------------------------------

# Hand-verified Devanagari for common first names where automatic
# transliteration is unreliable (keys are lowercase).
NAME_OVERRIDES = {
    "priya": "प्रिया", "kavya": "काव्या", "ananya": "अनन्या",
    "bhavya": "भव्या", "ramya": "रम्या", "soumya": "सौम्या",
    "saumya": "सौम्या", "karan": "करण", "krishna": "कृष्ण",
    "preeti": "प्रीति",
}

# Honorifics that should never be mistaken for the customer's name.
_NAME_HONORIFICS = {"mr", "mrs", "ms", "miss", "mx", "dr", "shri", "smt", "sri"}

# In-memory cache so repeated names don't re-hit the transliteration API.
_translit_cache = {}


def extract_first_name(full_name):
    """Returns a clean first name from a possibly messy full-name field."""
    if not full_name:
        return ""
    for token in str(full_name).split():
        # Keep only Latin/Devanagari letters — drops emojis, digits, punctuation.
        cleaned = re.sub(r"[^A-Za-zऀ-ॿ]", "", token)
        if cleaned and cleaned.lower() not in _NAME_HONORIFICS:
            return cleaned
    return ""


def _has_devanagari(text):
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def transliterate_to_devanagari(name):
    """Transliterates a romanized first name to Devanagari for Hindi calls.

    Checks a hand-verified override list first, then Google Input Tools.
    Always falls back to the original name on failure so a call is never blocked.
    """
    if not name or _has_devanagari(name):
        return name

    key = name.lower()
    if key in NAME_OVERRIDES:
        return NAME_OVERRIDES[key]
    if key in _translit_cache:
        return _translit_cache[key]

    result = name  # safe fallback if the API is unavailable
    try:
        res = requests.get(
            "https://inputtools.google.com/request",
            params={"text": name, "itc": "hi-t-i0-und", "num": 1,
                    "cp": 0, "cs": 1, "ie": "utf-8", "oe": "utf-8"},
            timeout=5,
        )
        if res.status_code == 200:
            data = res.json()
            if data and data[0] == "SUCCESS" and data[1][0][1]:
                result = data[1][0][1][0]
    except Exception as e:
        print(f"⚠️ Name transliteration failed for '{name}': {e}")

    _translit_cache[key] = result
    return result


def call_ringg_ai(user, agent_id="3f3a9cc0-2362-440e-a6c4-8de4a8d99979", from_number_id="f77346c7-ba44-4470-a697-b90c72f5878f", scheduled_at=None):
    url = f"{BASE_URL}/ca/api/v0/calling/outbound/individual" 

    items = user.get("items", [])
    raw_title = items[0].get("title") if items else ""
    product_id = items[0].get("product_id") if items else None
    item_price = str(items[0].get("price", "")) if items else ""
    
    # Drop the trailing size suffix so the agent says just the shirt name
    spoken_title = strip_size_from_title(raw_title) if raw_title else ""
    
    # Fetch real-time data from Shopify
    product_data, metafields = fetch_shopify_product_data(product_id)
    body_html = product_data.get("body_html", "") if product_data else ""

    # Check whether the customer's size is in stock (passed to the agent)
    in_stock = get_stock_status(product_data, raw_title)
    
    # Extract Product Image URL
    product_image_url = ""
    if product_data:
        image_obj = product_data.get("image")
        if image_obj:
            product_image_url = image_obj.get("src", "")
        elif product_data.get("images"):
            product_image_url = product_data["images"][0].get("src", "")

    # Smarter detail extraction
    short_name, shirt_colour, shirt_fabric, shirt_fit = extract_shirt_details(raw_title, body_html, metafields)

    spoken_language = get_preferred_language(user.get("state", ""))

    # Speak only the first name, and transliterate it to Devanagari for Hindi
    # calls so the voice pronounces it naturally instead of reading English
    # letters with an English accent.
    raw_name = user.get("name") or "Customer"
    first_name = extract_first_name(raw_name) or "Customer"
    spoken_name = (
        transliterate_to_devanagari(first_name)
        if spoken_language == "hindi"
        else first_name
    )

    phone = str(user["phone"])
    if not phone.startswith("+"):
        phone = f"+91{phone[-10:]}"

    payload = {
        "name": raw_name,
        "mobile_number": phone,
        "agent_id": agent_id,
        "from_number_id": from_number_id,
        "custom_args_values": {
            # Round-trips back in the Ringg webhook so call results land on
            # this exact checkout doc, not "the latest doc for this phone".
            "checkout_id": str(user.get("_id", "")),
            "callee_name": spoken_name,
            # English first name — the WhatsApp message uses this, not the
            # Devanagari callee_name the voice agent uses for Hindi calls.
            "callee_name_en": first_name,
            "original_callee_name": raw_name,
            "shirt_name": spoken_title,
            "shirt_price": item_price,
            "language": spoken_language,
            "mobile_number": phone,
            "shirt_colour": shirt_colour,                
            "shirt_fabric": shirt_fabric,  
            "fit": shirt_fit,                  
            "recovery_url": user.get("recovery_url", ""),
            "product_image_url": product_image_url,
            "in_stock": in_stock
        },
        "call_config": {
            # retry_count: 0 — Ringg makes exactly one attempt. We own retries
            # in process_delayed_call so we can re-check Shopify for an order
            # before every redial and never call a customer who already ordered.
            "call_retry_config": {
                "retry_count": 0,
                "retry_busy": 30,
                "retry_not_picked": 30,
                "retry_failed": 30
            },
            "call_time": {
                "call_start_time": "09:00",
                "call_end_time": "22:00",
                "timezone": "Asia/Kolkata"
            }
        }
    }

    if scheduled_at:
        payload["call_config"]["call_time"]["scheduled_at"] = scheduled_at

    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        print(f"🚀 Sending call request to Ringg AI for {phone} (Scheduled: {scheduled_at})...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            print(f"✅ Ringg AI Response ({response.status_code}): Call successfully queued.")
            return True, response.json()
        else:
            print(f"❌ Ringg AI Error ({response.status_code}): {response.text}")
            return False, response.text
    except Exception as e:
        print(f"💥 Exception during Ringg AI call: {str(e)}")
        return False, str(e)