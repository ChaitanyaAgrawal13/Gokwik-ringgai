from datetime import datetime

def create_checkout(data):
    return {
        "phone": data.get("phone"),
        "name": data.get("name"),
        "cart_value": data.get("cart_value"),
        "created_at": datetime.utcnow(),
        "called": False,
        "call_attempts": 0,
        "last_called_at": None,
        "last_error": None
    }