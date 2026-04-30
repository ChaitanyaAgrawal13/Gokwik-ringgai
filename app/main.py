from fastapi import FastAPI, Request
from datetime import datetime
from app.db import collection
from app.models import create_checkout

app = FastAPI()

@app.post("/webhooks/gokwik")
async def gokwik_webhook(request: Request):
    data = await request.json()
    print("FULL PAYLOAD:", data)

    # Phone is nested in GoKwik payload
    customer = data.get("customer", {})
    phone = customer.get("phone") or data.get("address", {}).get("phone")

    if not phone:
        return {"status": "ignored"}

    # Dedup: same day
    existing = collection.find_one({
        "phone": phone,
        "created_at": {
            "$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)
        }
    })

    if existing:
        return {"status": "duplicate"}

    checkout = create_checkout(data)
    collection.insert_one(checkout)

    return {"status": "stored"}

@app.post("/webhooks/ringg")
async def ringg_webhook(request: Request):
    data = await request.json()
    event_type = data.get("event_type")
    
    print(f"📞 Received Ringg Event: {event_type}")

    if event_type == "all_processing_completed":
        analysis = data.get("client_analysis", {})
        
        # Check if customer asked for a message
        if analysis.get("whatsapp_message_asked") is True:
            custom_args = data.get("custom_args_values", {})
            
            phone = data.get("to_number")
            name = custom_args.get("callee_name", "Customer")
            product = custom_args.get("shirt_name", "your item")
            link = custom_args.get("recovery_url")
            image = custom_args.get("product_image_url")

            print(f"✅ Customer asked for link. Triggering WhatsApp to {phone}")
            
            from app.kwikengage import send_whatsapp_recovery
            send_whatsapp_recovery(phone, name, product, link, image)
            
            return {"status": "whatsapp_sent"}
            
    return {"status": "ignored"}