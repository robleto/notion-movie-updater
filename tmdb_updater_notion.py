import os
import requests
import time
from notion_client import Client

# --- SETTINGS ---
NOTION_TOKEN = os.environ['NOTION_API_KEY']
DATABASE_ID = os.environ['NOTION_DATABASE_ID']
TMDB_API_KEY = os.environ['TMDB_API_KEY']

SEARCH_URL = 'https://api.themoviedb.org/3/search/movie'
DETAILS_URL = 'https://api.themoviedb.org/3/movie/{movie_id}'
CREDITS_URL = 'https://api.themoviedb.org/3/movie/{movie_id}/credits'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'

notion = Client(auth=NOTION_TOKEN)

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

def search_movie(title, year=None):
    params = {
        'api_key': TMDB_API_KEY,
        'query': title,
        'include_adult': False,
    }
    if year and year.isdigit():
        params['year'] = int(year)
    response = requests.get(SEARCH_URL, params=params)
    if response.status_code == 200:
        results = response.json().get('results')
        if results:
            return results[0]['id']
    return None

def get_movie_details(movie_id):
    response = requests.get(DETAILS_URL.format(movie_id=movie_id), params={'api_key': TMDB_API_KEY})
    if response.status_code == 200:
        return response.json()
    return None

def get_movie_credits(movie_id):
    response = requests.get(CREDITS_URL.format(movie_id=movie_id), params={'api_key': TMDB_API_KEY})
    if response.status_code == 200:
        return response.json()
    return None

def format_currency(value):
    if value is None or value == 0:
        return None
    return "${:,.0f}".format(value)

def get_text(p):
    return p[0]['plain_text'].strip() if p else ''

def fill_missing_movies():
    print("🔍 Checking Notion for missing movie data...")
    response = notion.databases.query(
        database_id=DATABASE_ID,
        filter={"or": [
            {"property": "Overview", "rich_text": {"is_empty": True}},
            {"property": "Art", "files": {"is_empty": True}}
        ]}
    )
    pages = response.get("results", [])
    print(f"📄 Found {len(pages)} movies to process")

    for idx, page in enumerate(pages):
        props = page['properties']
        page_id = page['id']        
        title = get_text(props['Title']['title']) if 'Title' in props else None
        year = get_text(props['Year']['rich_text']) if 'Year' in props else None

        if not title:
            print(f"⚠️ Skipping row with no title: {page_id}")
            continue

        print(f"🎬 [{idx + 1}/{len(pages)}] Processing: {title} ({year})")

        movie_id = search_movie(title, year)
        if not movie_id:
            print(f"❌ Movie not found: {title}")
            continue

        details = get_movie_details(movie_id)
        credits = get_movie_credits(movie_id)

        updates = {}

        if details:
            if not props.get('Genre') or not props['Genre']['multi_select']:
                genres = details.get('genres')
                if genres:
                    updates['Genre'] = {'multi_select': [{'name': g['name']} for g in genres]}

            if not props.get('Rating') or props['Rating'].get('number') is None:
                rating = details.get('vote_average')
                if rating is not None:
                    updates['Rating'] = {'number': rating}

            if not props.get('Overview') or not props['Overview']['rich_text']:
                overview = details.get('overview')
                if overview:
                    updates['Overview'] = {'rich_text': [{'text': {'content': overview}}]}

            if not props.get('Runtime') or props['Runtime'].get('number') is None:
                runtime = details.get('runtime')
                if runtime:
                    updates['Runtime'] = {'number': runtime}

            if not props.get('Art') or not props['Art']['files']:
                poster_path = details.get('poster_path')
                if poster_path:
                    updates['Art'] = {'files': [{'name': 'poster', 'external': {'url': f"{IMAGE_BASE_URL}{poster_path}"}}]}

            if not props.get('Gross') or not props['Gross']['rich_text']:
                revenue = details.get('revenue')
                if revenue:
                    updates['Gross'] = {'rich_text': [{'text': {'content': format_currency(revenue)}}]}

            if not props.get('Studio') or not props['Studio']['rich_text']:
                companies = details.get('production_companies', [])
                if companies:
                    original_studio = companies[0]['name']
                    updates['Studio'] = {'rich_text': [{'text': {'content': standardize_studio(original_studio)}}]}

        if credits:
            crew = credits.get('crew', [])
            if not props.get('Director') or not props['Director']['rich_text']:
                directors = [p['name'] for p in crew if p['job'] == 'Director']
                if directors:
                    updates['Director'] = {'rich_text': [{'text': {'content': directors[0]}}]}

            cast = credits.get('cast', [])
            for i in range(4):
                key = f"Star{i+1}"
                if key in props and (not props[key]['rich_text']):
                    if i < len(cast):
                        updates[key] = {'rich_text': [{'text': {'content': cast[i]['name']}}]}

        if updates:
            notion.pages.update(page_id=page_id, properties=updates)
            print(f"✅ Updated: {title}")
        else:
            print(f"🟡 No updates needed: {title}")

        time.sleep(0.25)

if __name__ == "__main__":
    fill_missing_movies()
