from notion_client import Client
import os
from dotenv import load_dotenv

# Load environment variables from .env if running locally
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
MOVIES_DB = os.getenv("MOVIES_DB_ID")
GENRES_DB = os.getenv("GENRES_DB_ID")

notion = Client(auth=NOTION_API_KEY)

if not GENRES_DB:
    raise ValueError("❌ Missing GENRES_DATABASE_ID environment variable")


def get_all_pages(database_id, filter=None):
    all_results = []
    start_cursor = None

    while True:
        query_params = {
            "database_id": database_id,
            "page_size": 100,
        }
        if filter:
            query_params["filter"] = filter
        if start_cursor:
            query_params["start_cursor"] = start_cursor

        response = notion.databases.query(**query_params)
        all_results.extend(response.get("results", []))

        if not response.get("has_more"):
            break

        start_cursor = response.get("next_cursor")

    return all_results

def build_genre_lookup():
    genre_pages = get_all_pages(GENRES_DB)
    lookup = {}
    for page in genre_pages:
        name = page["properties"]["Name"]["title"][0]["plain_text"]
        lookup[name.lower()] = page["id"]
    return lookup

def link_genres():
    print("🔗 Linking genre tags with Notion genre relations...")

    genre_lookup = build_genre_lookup()
    movies = get_all_pages(MOVIES_DB)

    for movie in movies:
        props = movie["properties"]
        title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "Untitled")
        page_id = movie["id"]

        genre_tags = props.get("Genre", {}).get("multi_select", [])
        existing_relations = props.get("Genres", {}).get("relation", [])

        # Skip if already linked or no tags
        if genre_tags and not existing_relations:
            related_ids = []
            for tag in genre_tags:
                genre_name = tag["name"].lower()
                genre_id = genre_lookup.get(genre_name)
                if genre_id:
                    related_ids.append({"id": genre_id})

            if related_ids:
                notion.pages.update(
                    page_id=page_id,
                    properties={
                        "Genres": {
                            "relation": related_ids
                        }
                    }
                )
                print(f"✅ Updated: {title}")
            else:
                print(f"⚠️ No genre matches found for: {title}")
        else:
            print(f"⏩ Skipped: {title} (already linked or no tags)")

if __name__ == "__main__":
    link_genres()
