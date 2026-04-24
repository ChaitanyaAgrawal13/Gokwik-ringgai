from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
print("ENV CHECK:", os.environ)
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

if not MONGO_URI or not DB_NAME:
    raise ValueError(f"Missing DB Credentials! MONGO_URI: {bool(MONGO_URI)}, DB_NAME: {bool(DB_NAME)}. Env keys available: {list(os.environ.keys())}")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

collection = db["checkouts"]