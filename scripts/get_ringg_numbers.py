import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RINGG_API_KEY")
BASE_URL = os.getenv("RINGG_BASE_URL")

def get_numbers():
    print("Fetching phone numbers from Ringg Workspace...")
    url = f"{BASE_URL}/ca/api/v0/workspace/numbers"
    headers = {"X-API-KEY": API_KEY}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        numbers = data.get("workspace_numbers", [])
        if not numbers:
            print("❌ No phone numbers found in this workspace!")
        else:
            print("✅ Found Available Numbers:")
            for num in numbers:
                print(f"  Phone Number: {num.get('number')}")
                print(f"  from_number_id: {num.get('id')}")
                print("-" * 50)
    else:
        print(f"❌ Failed to fetch numbers: [{response.status_code}] {response.text}")

if __name__ == "__main__":
    get_numbers()
