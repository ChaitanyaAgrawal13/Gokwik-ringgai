from datetime import datetime

def create_checkout(data):
    customer = data.get("customer", {})
    address = data.get("address", {})
    phone = customer.get("phone") or address.get("phone")
    name = f"{customer.get('firstname', '')} {customer.get('lastname', '')}".strip()
    
    # Extract items/products 
    raw_items = data.get("items", [])
    items = []
    for item in raw_items:
        items.append({
            "title": item.get("title"),
            "price": item.get("price", 0) / 100, # Converting paisa to INR usually if it's 99900 -> 999
            "quantity": item.get("quantity", 1)
        })

    return {
        "phone": phone,
        "name": name,
        "cart_value": data.get("total_price"),
        "items": items,
        "recovery_url": data.get("abc_url"),
        "city": address.get("city"),
        "state": address.get("state"),
        "created_at": datetime.utcnow(),
        "called": False,
        "call_attempts": 0,
        "last_called_at": None,
        "last_error": None
    }