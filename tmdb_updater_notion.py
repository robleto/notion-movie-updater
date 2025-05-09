import os
import re
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

def get_text(p):
    try:
        return str(p[0]['plain_text']).strip()
    except (IndexError, KeyError, TypeError):
        return ''

def clean_title(title):
    return re.sub(r"[^\w\s:]", '', title).strip()

def search_movie(title, year=None):
    if not title:
        return None
    clean = clean_title(title)

    params = {
        'api_key': TMDB_API_KEY,
        'query': clean,
        'include_adult': False,
    }

    if year and year.isdigit():
        params['year'] = int(year)

    print(f"📦 Searching TMDB: '{clean}' | Year: {year}")
    response = requests.get(SEARCH_URL, params=params)
    if response.status_code == 200:
        results = response.json().get('results', [])
        if results:
            return results[0]['id']

    print(f"🔁 Retry without year: '{clean}'")
    response = requests.get(SEARCH_URL, params={
        'api_key': TMDB_API_KEY,
        'query': clean,
        'include_adult': False,
    })
    if response.status_code == 200:
        results = response.json().get('results', [])
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
            # Genre
            if not props.get('Genre') or not props['Genre']['multi_select']:
                genres = details.get('genres')
                if genres:
                    updates['Genre'] = {'multi_select': [{'name': g['name']} for g in genres]}

            # Rating
            rating_prop = props.get('Rating', {})
            if rating_prop.get('type') == 'number':
                current_rating = rating_prop.get('number')
                if current_rating is None or current_rating == 0:
                    rating = details.get('vote_average')
                    if rating is not None and rating > 0:
                        updates['Rating'] = {'number': rating}

            # Overview
            if not props.get('Overview') or not props['Overview']['rich_text']:
                overview = details.get('overview')
                if overview:
                    updates['Overview'] = {'rich_text': [{'text': {'content': overview}}]}

            # Runtime
            runtime_prop = props.get('Runtime', {})
            if runtime_prop.get('type') == 'number':
                current_runtime = runtime_prop.get('number')
                if current_runtime is None or current_runtime == 0:
                    runtime = details.get('runtime')
                    if runtime is not None and runtime > 0:
                        updates['Runtime'] = {'number': runtime}

            # Poster Art
            if not props.get('Art') or not props['Art']['files']:
                poster_path = details.get('poster_path')
                if poster_path:
                    updates['Art'] = {'files': [{'name': 'poster', 'external': {'url': f"{IMAGE_BASE_URL}{poster_path}"}}]}

            # Gross
            if not props.get('Gross') or not props['Gross']['rich_text']:
                revenue = details.get('revenue')
                if revenue:
                    updates['Gross'] = {'rich_text': [{'text': {'content': format_currency(revenue)}}]}

            # Studio
            companies = details.get('production_companies', [])
            if companies:
                original_studio = companies[0]['name']
                standardized_studio = standardize_studio(original_studio)
                studio_prop = props.get('Studio', {})
                studio_type = studio_prop.get('type')

                if studio_type == 'select':
                    if not studio_prop.get('select'):
                        updates['Studio'] = {'select': {'name': standardized_studio}}
                else:
                    updates['Studio'] = {'rich_text': [{'text': {'content': standardized_studio}}]}

        if credits:
            # Director
            crew = credits.get('crew', [])
            if not props.get('Director') or not props['Director']['rich_text']:
                directors = [p['name'] for p in crew if p['job'] == 'Director']
                if directors:
                    updates['Director'] = {'rich_text': [{'text': {'content': directors[0]}}]}

            # Stars
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
