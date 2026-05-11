from fastapi import FastAPI, Request, BackgroundTasks
from datetime import datetime, timedelta, timezone
import asyncio
from app.db import collection
from app.models import create_checkout
from app.ringg import call_ringg_ai

# Define IST timezone (UTC+5:30)
IST_OFFSET = timezone(timedelta(hours=5, minutes=30))

app = FastAPI()

async def process_delayed_call(checkout):
    """
    Handles the 40-minute delay and night-time scheduling.
    If 40m delay lands in night (10PM-9AM), it waits until morning 9:15 AM IST.
    """
    try:
        from app.shopify_utils import has_completed_order
        
        phone = checkout.get("phone")
        email = checkout.get("email")
        # Convert datetime object to ISO string for Shopify
        abandoned_at = checkout.get("created_at").isoformat()
        
        # 1. Calculate intended call time (Now + 40 mins) in IST
        now_ist = datetime.now(IST_OFFSET)
        call_time = now_ist + timedelta(minutes=40)
        
        # 2. Check if this lands in the "Night Window" (22:00 to 09:00)
        is_night = False
        if call_time.hour >= 22 or call_time.hour < 9:
            is_night = True
            
        if is_night:
            # Calculate sleep until tomorrow 09:15 AM
            target_morning = call_time
            if call_time.hour >= 22:
                target_morning = call_time + timedelta(days=1)
            
            target_morning = target_morning.replace(hour=9, minute=15, second=0, microsecond=0)
            wait_seconds = (target_morning - now_ist).total_seconds()
            print(f"🌙 Night detected for {phone}. Scheduling call for morning 09:15 AM (Waiting {wait_seconds/3600:.1f} hours)")
        else:
            wait_seconds = 40 * 60 # 40 minutes
            print(f"⏳ Scheduling call for {phone} in 40 minutes.")

        # 3. Wait the required duration
        await asyncio.sleep(wait_seconds)
        
        # 4. Check if order already placed during the wait
        order_id = has_completed_order(email, phone, abandoned_at)
        if order_id:
            print(f"✅ Order {order_id} found for {phone} after wait! Skipping Ringg AI call.")
            return
            
        print(f"📞 No order found for {phone} since {abandoned_at}. Triggering Ringg AI call now.")
        success, res = call_ringg_ai(checkout)
        
        if success:
            collection.update_one(
                {"_id": checkout["_id"]},
                {"$set": {
                    "called": True,
                    "last_called_at": datetime.utcnow(),
                    "call_attempts": checkout.get("call_attempts", 0) + 1
                }}
            )
        else:
            print(f"❌ Failed to trigger Ringg call for {phone}: {res}")

    except Exception as e:
        print(f"💥 Error in delayed call process for {checkout.get('phone')}: {e}")

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
    print(f"FULL RINGG PAYLOAD: {data}")

    if event_type == "all_processing_completed":
        analysis = data.get("client_analysis") or {}
        call_duration = data.get("call_duration", 0)
        phone = data.get("to_number")
        transcript = data.get("transcript") or analysis.get("transcript", "")
        
        print(f"📊 Client Analysis Received: {analysis}")
        print(f"📝 Transcript: {transcript}")
        
        # Store analysis and transcript in DB
        collection.find_one_and_update(
            {"phone": phone[-10:]}, # Matching last 10 digits
            {"$set": {
                "call_analysis": analysis,
                "transcript": transcript,
                "call_duration": call_duration,
                "status": "called",
                "last_called_at": datetime.utcnow()
            }},
            sort=[("created_at", -1)] # Get most recent
        )
        
        # Check if customer asked for a message
        asked = analysis.get("whatsapp_message_asked")
        print(f"❓ WhatsApp Asked Flag: {asked} (Type: {type(asked)})")

        # FALLBACK LOGIC
        should_trigger_whatsapp = False
        trigger_reason = ""

        # Priority 1: AI explicitly flagged the request
        if asked is True or str(asked).lower() == "true":
            should_trigger_whatsapp = True
            trigger_reason = "AI Flag (True)"
        
        # Priority 2: Call duration > 40 seconds (Highly engaged customer)
        elif call_duration >= 40:
            should_trigger_whatsapp = True
            trigger_reason = f"High Engagement Fallback ({call_duration}s)"
            
        # Priority 3: Keywords in transcript (High intent for shorter calls)
        else:
            # Flatten transcript if it's a list (Ringg returns list of message objects)
            transcript_text = transcript
            if isinstance(transcript, list):
                transcript_text = " ".join([
                    (m.get("user") or m.get("bot") or "") 
                    for m in transcript 
                    if isinstance(m, dict)
                ])
            
            transcript_text = (transcript_text or "").lower()
            keywords = ["whatsapp", "link", "message", "send", "details", "price", "cost", "whatsapp number", "wa", "msg"]
            
            if any(kw in transcript_text for kw in keywords):
                should_trigger_whatsapp = True
                trigger_reason = f"Keyword Fallback (found in transcript)"

        if should_trigger_whatsapp:
            custom_args = data.get("custom_args_values", {})
            
            name = custom_args.get("callee_name", "Customer")
            product = custom_args.get("shirt_name", "your item")
            link = custom_args.get("recovery_url")
            image = custom_args.get("product_image_url")

            print(f"✅ Triggering WhatsApp via {trigger_reason} to {phone} for {product}")
            
            from app.kwikengage import send_whatsapp_recovery
            success, msg_id = send_whatsapp_recovery(phone, name, product, link, image)
            
            if success:
                collection.find_one_and_update(
                    {"phone": {"$regex": f"{phone[-10:]}$"}},
                    {"$set": {
                        "status": "whatsapp_sent",
                        "whatsapp_sent": True,
                        "whatsapp_message_id": msg_id,
                        "whatsapp_sent_at": datetime.utcnow(),
                        "trigger_reason": trigger_reason
                    }},
                    sort=[("created_at", -1)]
                )
            else:
                print(f"⚠️ WhatsApp API failed for {phone}. (SMS fallback disabled)")
                collection.find_one_and_update(
                    {"phone": {"$regex": f"{phone[-10:]}$"}},
                    {"$set": {
                        "status": "whatsapp_failed",
                        "last_error": "Kwikengage API failure",
                        "whatsapp_failed_at": datetime.utcnow(),
                        "trigger_reason": trigger_reason
                    }},
                    sort=[("created_at", -1)]
                )
            
            return {"status": "whatsapp_processed", "reason": trigger_reason}
        else:
            print("ℹ️ WhatsApp message not triggered: No request detected and duration too short.")
            
    return {"status": "ignored"}

@app.post("/webhooks/kwikengage")
async def kwikengage_webhook(request: Request):
    data = await request.json()
    print("📡 RECEIVED KWIKENGAGE DELIVERY STATUS:", data)
    
    status = data.get("status")
    msg_id = data.get("messageId") or data.get("id")
    
    if msg_id:
        # Look up the customer record by message ID to get phone
        record = collection.find_one({"whatsapp_message_id": msg_id})
        phone = record.get("phone") if record else f"untracked_msg_{msg_id}"
        
        update_data = {"whatsapp_delivery_status": status}
        
        if status == "failed":
            error_code = data.get("error_code")
            error_reason = data.get("error_reason") or "Delivery failed"
            print(f"❌ WhatsApp delivery failed for {phone} with error: {error_code} - {error_reason}")
            
            update_data["status"] = "whatsapp_failed"
            update_data["last_error"] = error_reason

            # Meta's Marketing Limit or Restricted Fallback
            critical_errors = ["whatsapp::error::131049", "whatsapp::error::131026"]
            if error_code in critical_errors or any(phrase in error_reason for phrase in ["Marketing Message Limit", "restricted by Meta", "Media upload error"]):
                print(f"❌ Critical WhatsApp failure ({error_code or error_reason}) for {phone}. (SMS fallback disabled)")

        elif status in ["delivered", "read", "seen"]:
            update_data["whatsapp_delivered"] = True
            
        if record:
            collection.update_one(
                {"whatsapp_message_id": msg_id},
                {"$set": update_data}
            )
        
    return {"status": "received"}