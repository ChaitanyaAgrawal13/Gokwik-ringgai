from datetime import datetime

def is_valid_call_time():
    hour = datetime.now().hour
    return 10 <= hour <= 20  # 10 AM – 8 PM