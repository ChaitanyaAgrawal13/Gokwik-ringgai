from datetime import datetime, timedelta
from app.db import collection
from app.ringg import call_ringg_ai
from app.utils import is_valid_call_time

def process_abandoned_checkouts():
    if not is_valid_call_time():
        print("Outside calling hours")
        return

    now = datetime.utcnow()

    users = collection.find({
        "called": False,
        "created_at": {"$lte": now - timedelta(minutes=30)},
        "cart_value": {"$gte": 800},
        "call_attempts": {"$lt": 2}
    })

    for user in users:
        success, response = call_ringg_ai(user)

        if success:
            collection.delete_one({"_id": user["_id"]})
            print(f"✅ Called and removed {user['phone']} from DB")
        else:
            collection.update_one(
                {"_id": user["_id"]},
                {
                    "$inc": {"call_attempts": 1},
                    "$set": {"last_error": response}
                }
            )
            print(f"❌ Failed {user['phone']}")