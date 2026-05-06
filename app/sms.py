import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Placeholder for SMS credentials (e.g. Msg91)
MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY")
MSG91_DLT_TE_ID = os.getenv("MSG91_DLT_TE_ID") # Template ID

def send_sms_fallback(phone, name, link):
    """
    Sends an SMS fallback when WhatsApp fails.
    Requires DLT registration for Indian numbers.
    """
    if not MSG91_AUTH_KEY:
        print("⚠️ SMS Fallback skipped: MSG91_AUTH_KEY missing.")
        return False
        
    print(f"📲 Attempting SMS Fallback to {phone}...")
    
    # Msg91 Example Structure
    # url = "https://api.msg91.com/api/v5/otp" # Or flow based API
    # payload = {
    #     "template_id": MSG91_DLT_TE_ID,
    #     "short_url": "1",
    #     "recipients": [{"mobiles": phone, "name": name, "link": link}]
    # }
    
    # For now, we log it until keys are provided
    print(f"📝 [MOCK SMS] Hi {name}, here is your checkout link: {link}")
    return True
