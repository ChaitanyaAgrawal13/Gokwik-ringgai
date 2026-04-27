import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("SHOPIFY_API_TOKEN")
product_id = "9370576093428" # The black knit shirt from the previous payload
url = f"https://kyyhe6-ry.myshopify.com/admin/api/2024-01/products/{product_id}.json"

headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    print("✅ SUCCESS! Connected to Shopify.")
    print("\n--- RAW PRODUCT DATA ---")
    print(f"Title: {data['product'].get('title')}")
    print(f"Tags: {data['product'].get('tags')}")
    print(f"Body HTML: {data['product'].get('body_html')}")
else:
    print(f"❌ Failed to connect: {response.status_code}")
    print(response.text)
