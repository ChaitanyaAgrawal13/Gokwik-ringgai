from fastapi import FastAPI, Request, BackgroundTasks
from datetime import datetime, timedelta
from app.db import collection
from app.models import create_checkout
from app.ringg import call_ringg_ai

app = FastAPI()

async def process_delayed_call(checkout):
    import asyncio
    from app.shopify_utils import has_completed_order
    
    phone = checkout.get("phone")
    email = checkout.get("email")
    # Convert datetime object to ISO string for Shopify
    abandoned_at = checkout.get("created_at").isoformat()
    
    print(f"⏳ Waiting 40 minutes before checking order status for {phone}...")
    await asyncio.sleep(40 * 60)
    
    order_id = has_completed_order(email, phone, abandoned_at)
    if order_id:
        print(f"✅ Order {order_id} found for {phone}! (Placed after abandonment at {abandoned_at}). Skipping Ringg AI call.")
        return
        
    print(f"📞 No order found for {phone} since {abandoned_at}. Triggering Ringg AI call now.")
    call_ringg_ai(checkout) # This calls immediately now

@app.post("/webhooks/gokwik")
async def gokwik_webhook(request: Request, background_tasks: BackgroundTasks):
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

    print(f"🕒 Background task started for {phone}. Will check & call in 40 mins.")
    background_tasks.add_task(process_delayed_call, checkout)

    return {"status": "stored_and_queued"}


@app.post("/webhooks/ringg")
async def ringg_webhook(request: Request):
    data = await request.json()
    event_type = data.get("event_type")
    
    print(f"📞 Received Ringg Event: {event_type}")

    if event_type == "all_processing_completed":
        analysis = data.get("client_analysis", {})
        call_duration = data.get("call_duration", 0)
        phone = data.get("to_number")
        
        print(f"📊 Client Analysis Received: {analysis}")
        
        # Store analysis in DB
        collection.find_one_and_update(
            {"phone": phone[-10:]}, # Matching last 10 digits
            {"$set": {
                "call_analysis": analysis,
                "call_duration": call_duration,
                "status": "called",
                "last_called_at": datetime.utcnow()
            }},
            sort=[("created_at", -1)] # Get most recent
        )
        
        # Check if customer asked for a message (handling both boolean and string "true")
        asked = analysis.get("whatsapp_message_asked")
        print(f"❓ WhatsApp Asked Flag: {asked} (Type: {type(asked)})")

        if asked is True or str(asked).lower() == "true":
            custom_args = data.get("custom_args_values", {})
            
            name = custom_args.get("callee_name", "Customer")
            product = custom_args.get("shirt_name", "your item")
            link = custom_args.get("recovery_url")
            image = custom_args.get("product_image_url")

            print(f"✅ Triggering WhatsApp to {phone} for {product}")
            
            from app.kwikengage import send_whatsapp_recovery
            success, msg_id = send_whatsapp_recovery(phone, name, product, link, image)
            
            if success:
                collection.find_one_and_update(
                    {"phone": phone[-10:]},
                    {"$set": {
                        "status": "whatsapp_sent",
                        "whatsapp_sent": True,
                        "whatsapp_message_id": msg_id,
                        "whatsapp_sent_at": datetime.utcnow()
                    }},
                    sort=[("created_at", -1)]
                )
            else:
                collection.find_one_and_update(
                    {"phone": phone[-10:]},
                    {"$set": {
                        "status": "whatsapp_failed",
                        "last_error": "Kwikengage API failure (likely Meta restriction)",
                        "whatsapp_failed_at": datetime.utcnow()
                    }},
                    sort=[("created_at", -1)]
                )
            
            return {"status": "whatsapp_processed"}
        else:
            print("ℹ️ WhatsApp message not requested by customer according to AI analysis.")
            
    return {"status": "ignored"}

@app.post("/webhooks/kwikengage")
async def kwikengage_webhook(request: Request):
    data = await request.json()
    print("📡 RECEIVED KWIKENGAGE DELIVERY STATUS:", data)
    
    # Typically includes: status, messageId, to
    status = data.get("status")
    msg_id = data.get("messageId") or data.get("id")
    phone = data.get("to")
    
    if msg_id:
        update_data = {"whatsapp_delivery_status": status}
        if status == "failed":
            update_data["status"] = "whatsapp_failed"
            update_data["last_error"] = data.get("error") or "Delivery failed"
        elif status in ["delivered", "read"]:
            update_data["whatsapp_delivered"] = True
            
        collection.update_one(
            {"whatsapp_message_id": msg_id},
            {"$set": update_data}
        )
        
    return {"status": "received"}