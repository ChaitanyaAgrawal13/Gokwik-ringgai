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
        return False

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    import urllib.parse
    # Add UTM parameters to the recovery URL
    if "?" in recovery_url:
        tracked_url = f"{recovery_url}&utm_source=ringg_ai&utm_medium=whatsapp&utm_campaign=recovery"
    else:
        tracked_url = f"{recovery_url}?utm_source=ringg_ai&utm_medium=whatsapp&utm_campaign=recovery"

    # URL encode the body link to prevent WhatsApp markdown issues
    safe_body_url = tracked_url.replace("_", "%5F")

    # Clean the image URL (remove Shopify versioning like ?v=...)
    clean_image_url = image_url.split("?")[0] if image_url else "https://cdn.shopify.com/s/files/1/0778/6158/5140/files/Oxfordgrey.png"

    # Prepare the payload
    payload = {
        "to": phone,
        "channel": "whatsapp",
        "content": {
            "type": "template",
            "template": {
                "template_id": TEMPLATE_ID,
                "language": "en",
                "components": [
                    {
                        "type": "button",
                        "sub_type": "url",
                        "parameters": [
                            {
                                "type": "text",
                                "text": tracked_url.split("/")[-1] if "/" in tracked_url else tracked_url
                            }
                        ],
                        "index": 0
                    },
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
                            {"type": "text", "text": product_name},   # {{2}}
                            {"type": "text", "text": safe_body_url}   # {{3}}
                        ]
                    }
                ]
            }
        },
        "meta_data": {
            "destination_url": tracked_url
        }
    }

    try:
        response = requests.post(BASE_URL, headers=headers, json=payload, timeout=10)
        print(f"📡 Kwikengage Response ({response.status_code}):", response.text)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Kwikengage Error: {e}")
        return False
