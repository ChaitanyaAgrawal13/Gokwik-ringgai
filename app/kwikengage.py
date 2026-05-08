import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KWIKENGAGE_API_KEY")
TEMPLATE_ID = os.getenv("KWIKENGAGE_TEMPLATE_ID")
BASE_URL = "https://api.kwikengage.ai/send-message/v2"

def send_whatsapp_recovery(phone, name, product_name, recovery_url, image_url):
    """Sends a WhatsApp recovery message via Kwikengage."""
    if not API_KEY or not TEMPLATE_ID:
        print("❌ Kwikengage credentials missing")
        return False, None

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    # Add UTM parameters to the recovery URL
    if "?" in recovery_url:
        tracked_url = f"{recovery_url}&utm_source=ringg_ai&utm_medium=whatsapp&utm_campaign=recovery"
    else:
        tracked_url = f"{recovery_url}?utm_source=ringg_ai&utm_medium=whatsapp&utm_campaign=recovery"

    # Clean and encode the image URL
    from urllib.parse import quote, urlparse, urlunparse
    if image_url:
        # Remove query params
        base_url = image_url.split("?")[0]
        # Encode spaces and special chars in path
        parsed = urlparse(base_url)
        encoded_path = quote(parsed.path)
        clean_image_url = urlunparse(parsed._replace(path=encoded_path))
    else:
        clean_image_url = "https://cdn.shopify.com/s/files/1/0778/6158/5140/files/Oxfordgrey.png"

    # Normalize phone number (handle +91, 91, or just 10 digits)
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if len(clean_phone) == 10:
        to_phone = f"+91{clean_phone}"
    elif len(clean_phone) == 12 and clean_phone.startswith("91"):
        to_phone = f"+{clean_phone}"
    else:
        to_phone = f"+{clean_phone}" if not phone.startswith("+") else phone

    # Prepare the payload according to Kwikengage v2 structure
    payload = {
        "to": to_phone,
        "channel": "whatsapp",
        "content": {
            "type": "template",
            "template": {
                "template_id": TEMPLATE_ID,
                "language": "en",
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "media",
                                "media": {
                                    "type": "image",
                                    "url": clean_image_url
                                }
                            }
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": name},          # {{1}}
                            {"type": "text", "text": product_name}    # {{2}}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": 0,
                        "parameters": [
                            {
                                "type": "text",
                                "text": tracked_url.split("/")[-1] if "/" in tracked_url else tracked_url
                            }
                        ]
                    }
                ]
            }
        }
    }

    try:
        response = requests.post(BASE_URL, headers=headers, json=payload, timeout=10)
        if response.status_code in [200, 201, 202]:
            try:
                res_data = response.json()
                print(f"✅ KWIKENGAGE API RESPONSE: {res_data}")
                # Extract message ID (tried multiple common fields)
                msg_id = res_data.get('message_id_attr') or res_data.get('messageId') or res_data.get('id')
                if not msg_id and res_data.get('data'):
                    data = res_data.get('data')
                    msg_id = data if isinstance(data, str) else data.get('messageId')
                return True, msg_id
            except Exception as e:
                print(f"⚠️ Error parsing Kwikengage response: {e}")
                return True, None
        else:
            print(f"❌ Kwikengage Error ({response.status_code}): {response.text}")
            return False, None
    except Exception as e:
        print(f"❌ Kwikengage Error: {e}")
        return False, None
