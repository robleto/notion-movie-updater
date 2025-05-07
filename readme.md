# 🎬 Notion Movie Auto-Updater

Automatically enrich your Notion movie database with movie details and poster art from [TMDB (The Movie Database)](https://www.themoviedb.org/), using GitHub Actions and a Python script.

This project fills in missing metadata for movies you add to Notion — all you need to provide is the title and year.

---

## 🔧 What It Does

For each movie entry that is missing key fields, the script will:

- Look up the movie on TMDB using its title (and year, if available)
- Pull details including:
  - ✅ Overview
  - 🎭 Genre(s)
  - ⭐ Average rating
  - 🕒 Runtime
  - 🧑‍🎤 Director & top 4 stars
  - 🏢 Studio name (with optional normalization)
  - 💰 Box office gross
  - 🖼️ Poster art
- Update those fields in your Notion database

The script skips fields that are already filled or are clearly invalid (like zero runtime or rating).

---

## ✅ Requirements

You’ll need:

- A **Notion integration** with access to your database
- A **TMDB API key** from [TMDB's developer portal](https://www.themoviedb.org/settings/api)
- A Notion database with columns for title, year, and the metadata fields you'd like filled

---

## 🪜 Setup Guide

### 1. Prepare Your Notion Database

- Add at least a `Title` (text) and `Year` (text or number) column
- Add columns for any of the following, using the appropriate types:
  - `Overview` – text
  - `Genre` – multi-select
  - `Rating` – number
  - `Runtime` – number
  - `Gross` – text
  - `Poster_art` – files & media
  - `Studio` – text or select
  - `Director`, `Star1`, `Star2`, `Star3`, `Star4` – text

- Share your Notion database with your integration under **Share → Invite → [Your Integration]**

### 2. Fork or Clone This Repo

```bash git clone https://github.com/YOUR_USERNAME/notion-movie-updater.git```

### 3. Add Your Secrets in GitHub

Go to your GitHub repo → **Settings → Secrets and variables → Actions**, and add the following:

- `NOTION_API_KEY` — your Notion integration token  
- `NOTION_DATABASE_ID` — the ID from your Notion database URL  
- `TMDB_API_KEY` — your API key from TMDB  

---

## 🧠 Tips

- Movies must have a **Title**. Year improves search accuracy but is optional.
- Poster art URLs are pulled directly from TMDB’s CDN and inserted into your Files & Media column.
- Runtime and Rating values of 0 are assumed to be invalid and will trigger a retry or be skipped.
- Studio names are optionally standardized into parent companies like "Disney", "Sony", etc.

## 🧱 Example Column Mapping

| Notion Property | Type           | Populated From TMDB               |
|-----------------|----------------|-----------------------------------|
| Title           | Text           | Required to search                |
| Year            | Text/Number    | Used to narrow the match          |
| Overview        | Text           | Overview of the movie             |
| Genre           | Multi-select   | Genres assigned on TMDB           |
| Rating          | Number         | Average rating from TMDB          |
| Runtime         | Number         | Movie duration in minutes         |
| Gross           | Text           | Box office (e.g. "$175,000,000")  |
| Poster_art      | Files/Media    | Poster image URL                  |
| Studio          | Text/Select    | Primary production company        |
| Director        | Text           | First credited director           |
| Star1–Star4     | Text           | First four credited cast          |

## 📣 Contribute

Suggestions, forks, and PRs welcome!  
If you use this for your own movie tracker or ranking tool - share it! I’d love to see what you build.

## 📄 License

MIT - free to use and modify, just don’t include your API keys in public code.
