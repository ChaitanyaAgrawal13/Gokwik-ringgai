from datetime import datetime

def create_checkout(data):
    customer = data.get("customer", {})
    phone = customer.get("phone") or data.get("address", {}).get("phone")
    name = f"{customer.get('firstname', '')} {customer.get('lastname', '')}".strip()
    
    return {
        "phone": phone,
        "name": name,
        "cart_value": data.get("total_price"),
        "created_at": datetime.utcnow(),
        "called": False,
        "call_attempts": 0,
        "last_called_at": None,
        "last_error": None
    }