#!/usr/bin/env python3
"""
Seed the MongoDB collection with a small number of scraped articles.
This script uses the existing `webscapper.scrape` function but limits the count
so it completes quickly for local testing.
"""
import os
import dotenv
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from webscapper import scrape

dotenv.load_dotenv()

MONGO_URI = os.getenv("MONGO_DB_URI")
if not MONGO_URI:
    raise SystemExit("MONGO_DB_URI not set in environment")

# Use a short list / small count to keep runtime low during testing
websites = [
    "https://www.ndtv.com/",
    "https://www.thequint.com/",
    "https://www.hindustantimes.com/",
]

COUNT_PER_SITE = 10

print("Connecting to MongoDB...")
client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
db = client["NewsBiasApp"]
collection = db["NewsArtciles"]

print(f"Scraping up to {COUNT_PER_SITE} articles per site ({len(websites)} sites)...")
results = scrape(websites, count=COUNT_PER_SITE)
valid_results = [r for r in results if r.get("title") and r.get("text")]
print(f"Scraped {len(results)} articles, {len(valid_results)} valid")

if not valid_results:
    print("No valid results to insert. Exiting.")
    raise SystemExit(0)

added_count = 0
duplicate_count = 0

try:
    res = collection.insert_many(valid_results, ordered=False)
    added_count = len(res.inserted_ids)
    duplicate_count = len(valid_results) - added_count
except BulkWriteError as bwe:
    write_errors = bwe.details.get("writeErrors", [])
    added_count = len(valid_results) - len(write_errors)
    duplicate_count = len(write_errors)
except Exception as e:
    print(f"Unexpected error inserting docs: {e}")
    raise

print(f"Inserted: {added_count}, duplicates (skipped): {duplicate_count}")

# cleanup similar to original: remove unwanted texts
unwanted_texts = ["", "Get App for Better Experience", "Log onto movie.ndtv.com for more celebrity pictures", "No description available."]
collection.delete_many({"title": {"$exists": True, "$regex": "^(?i)(dell|hp|acer|lenovo)"}})
collection.delete_many({"text": {"$in": unwanted_texts}})

print("Seeding complete.")
