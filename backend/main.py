import os
import subprocess

# Ensure NLTK resources are downloaded
# subprocess.run(["python", "download_resources.py"])  # Commented out to avoid Anaconda conflicts

from flask import Flask, jsonify, request
import pandas as pd
from src.pipeline.predict_pipeline import PredictPipeline
from flask_cors import CORS
import webscapper
import json
from nltk.data import find
import nltk
from pymongo import MongoClient
from bson.json_util import dumps
from pymongo.errors import BulkWriteError
import dotenv

# Load environment variables
dotenv.load_dotenv()


def ensure_nltk_resource(resource_name):
    nltk_data_dir = os.path.join(
        os.path.dirname(
            os.path.abspath(
                __file__,
            )
        ),
        "nltk_data",
    )
    os.makedirs(
        nltk_data_dir,
        exist_ok=True,
    )

    if nltk_data_dir not in nltk.data.path:
        nltk.data.path.append(nltk_data_dir)

    try:
        find(resource_name)
        print(f"NLTK resource '{resource_name}' found")
    except LookupError:
        print(f"Warning: NLTK resource '{resource_name}' not found locally. Attempting download...")
        try:
            # Try with SSL workaround
            import ssl
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                pass
            else:
                ssl._create_default_https_context = _create_unverified_https_context
            
            nltk.download(
                resource_name,
                download_dir=nltk_data_dir,
            )
        except Exception as e:
            print(f"Could not download {resource_name}: {e}. Continuing anyway...")


ensure_nltk_resource("punkt")
ensure_nltk_resource("wordnet")
ensure_nltk_resource("stopwords")

# MongoDB setup
mongodb_url = str(os.getenv("MONGO_DB_URI"))
# Remove the old ssl_cert_reqs parameter that's causing warnings
client = MongoClient(mongodb_url, tlsAllowInvalidCertificates=True)
db = client["NewsBiasApp"]
collection = db["NewsArtciles"]

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*",
        },
    },
)


@app.route("/")
def home():
    """
    Handles the home route of the News Classifier API.
    Returns:
        Response: A JSON response containing a welcome message.
    """
    return jsonify(message="Welcome to the News Classifier API")


@app.route("/predict", methods=["POST"])
def bias():
    """
    Handles POST requests to the /predict endpoint to predict the bias of a given text.

    The function expects a JSON payload with 'title' and 'text' fields, combines them,
    and passes the combined text to the prediction pipeline.

    Returns:
        JSON: A JSON response containing the predicted bias or an error message.

    Raises:
        Exception: If there is an error during prediction, returns a JSON response with the error message and a 500 status code.
    """
    try:
        data = request.json
        pred = pd.DataFrame([data])
        pred["text"] = pred["title"] + pred["text"]
        predict_pipeline = PredictPipeline()

        # Pass the DataFrame column, not a scalar value
        result = predict_pipeline.predict(pred[["text"]])

        return jsonify(
            {
                "bias": result.tolist(),
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Failed to predict: {e}",
                }
            ),
            500,
        )


@app.route("/get-scrape", methods=["GET", "POST"])
def get_scrape():
    """
    Handles the '/get-scrape' endpoint for scraping articles from provided websites.
    This function accepts JSON data via GET or POST requests. The JSON data should contain:
    - 'websites': A list of website URLs to scrape.
    - 'count': (Optional) Maximum number of articles to fetch per website (default is 50).

    The function validates the input data, performs web scraping using the `webscapper.scrape` method,
    and filters out results that do not contain both 'title' and 'text'.

    Returns:
        JSON response:
        - 400 status code with an error message if the input data is invalid or empty.
        - 200 status code with a message if no valid results are found.
        - 200 status code with a message and the valid results if scraping is successful.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Invalid or empty JSON"}), 400

    websites = data.get("websites", [])
    count = data.get("count", 50)

    if not websites:
        return jsonify({"error": "No websites provided"}), 400

    results = webscapper.scrape(websites, count)
    valid_results = [r for r in results if r.get("title") and r.get("text")]

    if not valid_results:
        return (
            jsonify(
                {
                    "message": "No valid results to insert",
                }
            ),
            200,
        )

    return jsonify(
        {
            "message": "Scraping completed!",
            "results": valid_results,
        }
    )


@app.route("/scaper", methods=["GET", "POST"])
def scrape():
    """
    Scrapes articles from a list of websites and stores them in the database.
    This function handles both GET and POST requests. It expects a JSON payload with
    'websites' (a list of URLs to scrape) and 'count' (maximum number of articles to fetch per website).
    It validates the input, performs the scraping, filters out invalid results, and inserts the valid
    results into the database. It also handles duplicate entries and cleans up unwanted texts and
    excess documents in the collection.

    Returns:
        Response: A JSON response containing the status of the scraping operation, including the number
                of articles added and duplicates skipped.
    """
    data = request.json
    if not data:
        return (
            jsonify(
                {
                    "error": "Invalid or empty JSON",
                }
            ),
            400,
        )

    return jsonify(
        {
            "sucess": True,
            "message": "on cron job this function has been depricated in this version",
        }
    )

    websites = data.get("websites", [])
    count = data.get("count", 50)

    if not websites:
        return jsonify({"error": "No websites provided"}), 400

    results = webscapper.scrape(websites, count)
    valid_results = [r for r in results if r.get("title") and r.get("text")]

    if not valid_results:
        return jsonify({"message": "No valid results to insert"}), 200

    added_count = 0
    duplicate_count = 0

    try:
        result = collection.insert_many(valid_results, ordered=False)
        added_count = len(result.inserted_ids)
        duplicate_count = len(valid_results) - added_count

    except BulkWriteError as bwe:
        write_errors = bwe.details.get("writeErrors", [])
        added_count = len(valid_results) - len(write_errors)
        duplicate_count = len(write_errors)

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    unwanted_texts = [
        "",
        "Get App for Better Experience",
        "Log onto movie.ndtv.com for more celebrity pictures",
        "No description available.",
    ]

    collection.delete_many(
        {"title": {"$exists": True, "$regex": "^(?i)(dell|hp|acer|lenovo)"}}
    )
    collection.delete_many({"text": {"$in": unwanted_texts}})

    total_count = collection.count_documents({})
    if total_count > 1500:
        excess_docs = total_count - 1500
        oldest_docs = (
            collection.find({}, {"_id": 1}).sort("published_date", 1).limit(excess_docs)
        )
        doc_ids = [doc["_id"] for doc in oldest_docs]
        if doc_ids:
            collection.delete_many({"_id": {"$in": doc_ids}})

    return jsonify(
        {
            "message": "Scraping completed!",
            "added_articles": added_count,
            "duplicates_skipped": duplicate_count,
        }
    )


@app.route("/cache", methods=["GET", "OPTIONS"])
def cache():
    """
    Retrieves cached data from the database, sorted by published date in descending order.

    Returns:
        Response: A JSON response containing the cached data if available,
                or an error message if no cached data is found or if an exception occurs.
    """
    try:
        entire_data = list(collection.find().sort("published_date", -1))
        if not entire_data:
            return (
                jsonify(
                    {
                        "error": "No cached data found. Please scrape first.",
                    }
                ),
                404,
            )
        return jsonify(json.loads(dumps(entire_data)))

    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Failed to retrieve cached data: {e}",
                }
            ),
            500,
        )


@app.route("/search", methods=["POST"])
def search():
    """
    Handles the search functionality for articles based on a keyword.

    This endpoint expects a JSON payload with a 'keyword' field. It searches the articles
    collection for matches in the 'title' and 'text' fields using MongoDB's text search.
    The results are sorted by their relevance score.

    Args:
        None

    Returns:
        Response: A JSON response containing the search results or an error message.
        - 200: A list of articles matching the search keyword.
        - 400: If no keyword is provided in the request.
        - 404: If no articles are found matching the keyword.
        - 500: If an error occurs during the search process.
    """
    data = request.json
    if not data:
        return (
            jsonify(
                {"error": "Invalid or empty JSON"},
            ),
            400,
        )

    keyword = data.get("keyword")

    if not keyword:
        return (
            jsonify(
                {"error": "No keyword provided"},
            ),
            400,
        )

    try:
        collection.create_index([("title", "text"), ("text", "text")])

        results = collection.find(
            {"$text": {"$search": keyword}}, {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})])

        articles = list(results)
        if not articles:
            return (
                jsonify(
                    {
                        "message": "No articles found",
                    }
                ),
                404,
            )
        return jsonify(json.loads(dumps(articles)))

    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Search failed: {e}",
                }
            ),
            500,
        )


@app.route("/delete", methods=["DELETE"])
def delete():
    """
    Deletes the oldest 1000 documents from the collection based on the published date.
    This function retrieves the oldest 1000 documents from the MongoDB collection,
    deletes them, and returns a JSON response indicating the number of documents deleted.
    Returns:
        Response: A JSON response containing a message with the number of deleted documents
                or an error message if the deletion fails.
    """
    try:
        oldest_docs = collection.find().sort("published_date", 1).limit(1000)

        doc_ids = [doc["_id"] for doc in oldest_docs]

        if doc_ids:
            result = collection.delete_many({"_id": {"$in": doc_ids}})
            return jsonify(
                {
                    "message": f"Deleted {result.deleted_count} documents",
                }
            )

        return jsonify(
            {
                "message": "No documents to delete",
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Failed to delete documents: {e}",
                }
            ),
            500,
        )


if __name__ == "__main__":
    print(" * Starting News Bias Detector Backend")
    print(" * Running on http://127.0.0.1:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
