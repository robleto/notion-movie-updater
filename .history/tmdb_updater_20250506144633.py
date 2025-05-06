import os
import requests
from notion_client import Client
import time

# NEW: load from .env
from dotenv import load_dotenv
load_dotenv()
# This script updates a Notion database with movie details from TMDB.

# --- CONFIGURATION ---
NOTION_TOKEN = os.environ['NOTION_API_KEY']
DATABASE_ID = os.environ['NOTION_DATABASE_ID']
TMDB_API_KEY = os.environ['TMDB_API_KEY']

TMDB_SEARCH_URL = 'https://api.themoviedb.org/3/search/movie'
TMDB_DETAILS_URL = 'https://api.themoviedb.org/3/movie/{movie_id}'
TMDB_CREDITS_URL = 'https://api.themoviedb.org/3/movie/{movie_id}/credits'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'

STUDIO_MAPPING = {
    "Walt Disney Pictures": "Disney",
    "Walt Disney Animation Studios": "Disney",
    "Pixar Animation Studios": "Disney",
    "Marvel Studios": "Disney",
    "Lucasfilm Ltd.": "Disney",
    "20th Century Fox": "Fox",
    "20th Century Studios": "Fox",
    "DreamWorks Animation": "DreamWorks",
    "DreamWorks Pictures": "DreamWorks",
    "Columbia Pictures": "Sony",
    "Sony Pictures Animation": "Sony",
    "Sony Pictures Entertainment": "Sony",
    "Warner Bros. Pictures": "Warner Bros.",
    "New Line Cinema": "Warner Bros.",
    "Metro-Goldwyn-Mayer (MGM)": "MGM",
    "Universal Pictures": "Universal",
}

def standardize_studio(name):
    return STUDIO_MAPPING.get(name, name)

notion = Client(auth=NOTION_TOKEN)

def search_tmdb_movie(title, year):
    params = {
        'api_key': TMDB_API_KEY,
        'query': title,
        'year': year
    }
    response = requests.get(TMDB_SEARCH_URL, params=params)
    results = response.json().get('results', [])
    return results[0]['id'] if results else None

def get_tmdb_details(movie_id):
    url = TMDB_DETAILS_URL.format(movie_id=movie_id)
    res = requests.get(url, params={'api_key': TMDB_API_KEY})
    return res.json() if res.status_code == 200 else None

def get_tmdb_credits(movie_id):
    url = TMDB_CREDITS_URL.format(movie_id=movie_id)
    res = requests.get(url, params={'api_key': TMDB_API_KEY})
    return res.json() if res.status_code == 200 else None

def format_currency(value):
    return "${:,.0f}".format(value) if value else None

def update_notion_page(page_id, fields):
    try:
        notion.pages.update(page_id=page_id, properties=fields)
    except Exception as e:
        print(f"⚠️ Error updating page {page_id}: {e}")

def fill_missing_movies():
    print("🔍 Looking for movies missing data...")
    query = {
        "database_id": DATABASE_ID,
        "filter": {
            "property": "Overview",
            "rich_text": {"is_empty": True}
        }
    }
    pages = notion.databases.query(**query).get('results', [])
    print(f"📄 Found {len(pages)} incomplete movies")

    for page in pages:
        props = page['properties']
        page_id = page['id']
        title = props['Title']['title'][0]['plain_text'] if props['Title']['title'] else None
        year = props['Released_Year']['number'] if 'Released_Year' in props and props['Released_Year']['number'] else None

        if not title or not year:
            print(f"❌ Skipping: Missing title/year on page {page_id}")
            continue

        print(f"🎬 Processing: {title} ({year})")
        movie_id = search_tmdb_movie(title, year)
        if not movie_id:
            print(f"❌ TMDB not found: {title}")
            continue

        details = get_tmdb_details(movie_id)
        credits = get_tmdb_credits(movie_id)

        updates = {}

        if details:
            updates['Overview'] = {'rich_text': [{'text': {'content': details.get('overview', '')}}]}
            updates['Runtime'] = {'number': details.get('runtime')}
            updates['Rating'] = {'number': details.get('vote_average')}
            if details.get('revenue'):
                updates['Gross'] = {'rich_text': [{'text': {'content': format_currency(details.get('revenue'))}}]}
            if details.get('poster_path'):
                updates['Art'] = {'url': f"{IMAGE_BASE_URL}{details['poster_path']}"}
            if details.get('genres'):
                genre_names = [g['name'] for g in details['genres']]
                updates['Genre'] = {'multi_select': [{'name': g} for g in genre_names]}
            if details.get('production_companies'):
                studio = standardize_studio(details['production_companies'][0]['name'])
                updates['Studio'] = {'rich_text': [{'text': {'content': studio}}]}

        if credits:
            crew = credits.get('crew', [])
            directors = [p['name'] for p in crew if p['job'] == 'Director']
            if directors:
                updates['Director'] = {'rich_text': [{'text': {'content': directors[0]}}]}

            cast = credits.get('cast', [])
            for i in range(min(4, len(cast))):
                updates[f"Star{i+1}"] = {'rich_text': [{'text': {'content': cast[i]['name']}}]}

        update_notion_page(page_id, updates)
        time.sleep(0.25)  # Be nice to the API

if __name__ == '__main__':
    fill_missing_movies()
