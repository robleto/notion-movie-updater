import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

# Setup
notion = Client(auth=os.environ["NOTION_API_KEY"])
MOVIES_DB = os.environ["MOVIES_DB_ID"]
GENRES_DB = os.environ["GENRES_DB_ID"]

def build_genre_lookup():
    genre_lookup = {}
    genre_pages = notion.databases.query(database_id=GENRES_DB).get("results", [])
    for page in genre_pages:
        name_prop = page["properties"].get("Name", {})
        title = name_prop.get("title", [])
        if title:
            name = title[0]["plain_text"]
            genre_lookup[name] = page["id"]
    return genre_lookup

def link_genres():
    genre_lookup = build_genre_lookup()
    movies = notion.databases.query(database_id=MOVIES_DB).get("results", [])

    for movie in movies:
        props = movie["properties"]
        movie_id = movie["id"]

        if "Genre" not in props or "Genre Relation" not in props:
            continue

        multi_select = props["Genre"].get("multi_select", [])
        current_links = props["Genre Relation"].get("relation", [])

        if current_links or not multi_select:
            continue

        genre_names = [item["name"] for item in multi_select]
        related_ids = [ {"id": genre_lookup[name]} for name in genre_names if name in genre_lookup ]

        if related_ids:
            notion.pages.update(
                page_id=movie_id,
                properties={
                    "Genre Relation": {
                        "type": "relation",
                        "relation": related_ids
                    }
                }
            )
            title_val = props.get("Title", {}).get("title", [])
            if title_val:
                print(f"✅ Linked genres for: {title_val[0]['plain_text']}")

if __name__ == "__main__":
    print("🔗 Linking genre tags with Notion genre relations...")
    link_genres()
    print("🎉 Done!")
