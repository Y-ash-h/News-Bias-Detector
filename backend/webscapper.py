import os
import shutil
from nltk.data import find
import nltk
import newspaper
import json


def ensure_nltk_resource(resource_name):
    nltk_data_dir = os.path.join(
        os.path.dirname(
            os.path.abspath(
                __file__,
            )
        ),
        "nltk_data",
    )
    os.makedirs(nltk_data_dir, exist_ok=True)

    if nltk_data_dir not in nltk.data.path:
        nltk.data.path.append(nltk_data_dir)

    try:
        find(resource_name)

    except LookupError:
        print(f"Downloading NLTK resource: {resource_name}")
        nltk.download(resource_name, download_dir=nltk_data_dir)


ensure_nltk_resource("punkt")
ensure_nltk_resource("stopwords")

# Path to the cache folder
CACHE_FOLDER = os.path.join(
    os.path.dirname(__file__),
    ".newspaper_scraper",
)


def clear_cache():
    """
    Clears the newspaper cache folder to force fresh scraping of all articles.
    """
    if os.path.exists(CACHE_FOLDER):
        try:
            shutil.rmtree(CACHE_FOLDER)  # Delete the cache folder
            print("Cache cleared successfully.")

        except Exception as e:
            print(f"Failed to clear cache: {e}")

    else:
        print("No cache to clear.")


def scrape(websites: list, count: int = 50) -> list:
    """
    Scrapes articles from a list of websites and extracts metadata, including thumbnails.

    Args:
        websites (list): A list of website URLs to scrape.
        count (int): Maximum number of articles to fetch per website.

    Returns:
        list: A list of dictionaries, each containing metadata and content for an article.
    """
    articles_data = []
    temp = count

    for website in websites:
        temp = count
        try:
            site = newspaper.build(
                website,
                language="en",
                memorize=False,
            )
            print(f"Links from {website} = {len(site.articles)}")

            for article in site.articles:
                try:
                    if temp == 0:
                        break
                    article.download()
                    article.parse()
                    article.nlp()

                    articles_data.append(
                        {
                            "link": article.url,
                            "title": article.title,
                            "text": article.text,
                            "author": article.authors,
                            "publish_date": (
                                article.publish_date.strftime("%Y-%m-%d")
                                if article.publish_date
                                else None
                            ),
                            "keywords": article.keywords,
                            "tags": list(article.tags),
                            "thumbnail": article.top_image,
                        }
                    )
                    temp -= 1

                except Exception as e:
                    print(f"Failed to parse article: {article.url}. Error: {e}")
                    continue

        except Exception as e:
            print(f"Failed to process website: {website}. Error: {e}")
            continue

    print("**Finished Parsing**")
    print(f"Total Articles - {len(articles_data)}")
    return articles_data


def save_to_json(data, output_file):
    """
    Prepends the given data to an existing JSON file or creates a new file if none exists.

    Args:
        data (list): The data to save (list of dictionaries).
        output_file (str): The filename to save the data into.
    """
    try:

        if os.path.exists(output_file):
            with open(
                output_file,
                "r",
                encoding="utf-8",
            ) as json_file:
                existing_data = json.load(json_file)

        else:
            existing_data = []

        # Prepend new data to existing data
        combined_data = data + existing_data

        # Save updated data back to the file
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(combined_data, json_file, ensure_ascii=False, indent=4)

        print(f"Data saved to {output_file}")

    except Exception as e:
        print(f"Failed to save data to JSON. Error: {e}")


def main():
    import os
    import ssl
    import certifi
    import dotenv
    from pymongo import MongoClient
    from pymongo.errors import BulkWriteError

    dotenv.load_dotenv()
    mongodb_url = str(os.getenv("MONGO_DB_URI"))

    client = MongoClient(mongodb_url, tlsCAFile=certifi.where())
    db = client["newsBias"]
    collection = db["NewsArticles"]

    websites = [
        "https://www.ndtv.com/",
        "https://www.thequint.com/",
        "https://www.hindustantimes.com/",
        "https://www.opindia.com/",
        "https://timesofindia.indiatimes.com/",
        "https://www.republicworld.com/",
    ]

    results = scrape(websites, count=5000)
    valid_results = [r for r in results if r.get("title") and r.get("text")]

    if not valid_results:
        print("No valid results to insert")
        return

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
        print(f"Unexpected error: {str(e)}")
        return

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

    print(
        f"Scraping completed! Added articles: {added_count}, Duplicates skipped: {duplicate_count}"
    )


if __name__ == "__main__":
    main()
