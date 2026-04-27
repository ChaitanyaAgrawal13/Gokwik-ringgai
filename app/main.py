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