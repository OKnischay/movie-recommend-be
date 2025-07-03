# import os
# import csv
# import json
# import django
# from datetime import datetime

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
# django.setup()

# from movies.models import Movie, Genre


# # === Utility Functions ===
# def parse_json_list(text):
#     try:
#         return json.loads(text.replace("'", '"'))
#     except Exception:
#         return []

# def parse_date(date_str):
#     try:
#         return datetime.strptime(date_str, "%Y-%m-%d").date()
#     except:
#         return None

# # === Step 1: Load credits into a dict for fast lookup ===
# credits_path = './credits.csv'
# credits_dict = {}  # {movie_id: {"cast": [...], "crew": [...]}}

# with open(credits_path, 'r', encoding='utf-8') as f:
#     reader = csv.DictReader(f)
#     for row in reader:
#         try:
#             movie_id = int(row['movie_id'])
#             cast = parse_json_list(row['cast'])
#             crew = parse_json_list(row['crew'])
#             credits_dict[movie_id] = {
#                 "cast": cast,
#                 "crew": crew
#             }
#         except:
#             continue

# # === Step 2: Process movie metadata ===
# movies_path = './movies.csv'

# with open(movies_path, 'r', encoding='utf-8') as f:
#     reader = csv.DictReader(f)
#     for row in reader:
#         try:
#             tmdb_id = int(row['id'])
#             title = row['title']
#             overview = row['overview']
#             release_date = parse_date(row['release_date'])
#             runtime = int(float(row['runtime'])) if row['runtime'] else None
#             poster_url = row['homepage'] or ''

#             # Genres
#             genre_objs = []
#             genres_raw = parse_json_list(row['genres'])
#             for g in genres_raw:
#                 name = g.get('name')
#                 if name:
#                     genre_obj, _ = Genre.objects.get_or_create(name=name)
#                     genre_objs.append(genre_obj)

#             # Credits (cast + director)
#             credits = credits_dict.get(tmdb_id, {})
#             cast = credits.get('cast', [])
#             crew = credits.get('crew', [])

#             cast_names = [c['name'] for c in sorted(cast, key=lambda x: x.get('order', 0))[:5]]
#             director_names = [c['name'] for c in crew if c.get('job') == 'Director']
#             director = director_names[0] if director_names else ''

#             # Create movie
#             movie, created = Movie.objects.get_or_create(
#                 tmdb_id=tmdb_id,
#                 defaults={
#                     'title': title,
#                     'description': overview,
#                     'release_date': release_date,
#                     'duration': runtime or 0,
#                     'poster_url': poster_url,
#                     'director': director,
#                     'cast': cast_names,
#                 }
#             )

#             if created:
#                 movie.genres.set(genre_objs)
#                 print(f"✅ Added: {title}")
#             else:
#                 print(f"⚠️ Skipped (already exists): {title}")

#         except Exception as e:
#             print(f"❌ Error: {e} on row: {row.get('title')}")

import os
import csv
import json
import django
from datetime import datetime
from django.db import transaction

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from movies.models import Movie, Genre

# === Utility Functions ===
def parse_json_list(text):
    """Parse JSON-like string to Python list, handling common formatting issues"""
    if not text or text.strip() == '':
        return []
    try:
        # Replace single quotes with double quotes for valid JSON
        text = text.replace("'", '"')
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e} for text: {text[:100]}...")
        return []

def parse_date(date_str):
    """Parse date string to date object"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError as e:
        print(f"Date parsing error: {e} for date: {date_str}")
        return None

def safe_int_convert(value, default=None):
    """Safely convert value to integer"""
    if not value or str(value).strip() == '':
        return default
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default

# === Step 1: Load credits into a dict for fast lookup ===
print("Loading credits data...")
credits_path = './credits.csv'
credits_dict = {}  # {movie_id: {"cast": [...], "crew": [...]}}

try:
    with open(credits_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, 1):
            try:
                movie_id = safe_int_convert(row.get('movie_id'))
                if movie_id is None:
                    continue
                    
                cast = parse_json_list(row.get('cast', ''))
                crew = parse_json_list(row.get('crew', ''))
                
                credits_dict[movie_id] = {
                    "cast": cast,
                    "crew": crew
                }
            except Exception as e:
                print(f"Error processing credits row {row_num}: {e}")
                continue
    
    print(f"Loaded credits for {len(credits_dict)} movies")
except FileNotFoundError:
    print(f"Credits file not found: {credits_path}")
    credits_dict = {}
except Exception as e:
    print(f"Error loading credits: {e}")
    credits_dict = {}

# === Step 2: Process movie metadata ===
print("Processing movies data...")
movies_path = './movies.csv'
success_count = 0
error_count = 0
skip_count = 0

try:
    with open(movies_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Use transaction for better performance and data integrity
        with transaction.atomic():
            for row_num, row in enumerate(reader, 1):
                try:
                    # Extract and validate basic movie data
                    tmdb_id = safe_int_convert(row.get('id'))
                    if tmdb_id is None:
                        print(f"Row {row_num}: Invalid or missing movie ID")
                        error_count += 1
                        continue
                    
                    title = row.get('title', '').strip()
                    if not title:
                        print(f"Row {row_num}: Missing title for movie ID {tmdb_id}")
                        error_count += 1
                        continue
                    
                    overview = row.get('overview', '').strip()
                    release_date = parse_date(row.get('release_date'))
                    runtime = safe_int_convert(row.get('runtime'), 0)
                    poster_url = row.get('homepage', '').strip()
                    
                    # Process genres
                    genre_objs = []
                    genres_raw = parse_json_list(row.get('genres', ''))
                    
                    for g in genres_raw:
                        if isinstance(g, dict) and 'name' in g:
                            genre_name = g['name'].strip()
                            if genre_name:
                                genre_obj, created = Genre.objects.get_or_create(name=genre_name)
                                genre_objs.append(genre_obj)
                    
                    # Process credits (cast + director)
                    credits = credits_dict.get(tmdb_id, {})
                    cast = credits.get('cast', [])
                    crew = credits.get('crew', [])
                    
                    # Get top 5 cast members ordered by their 'order' field
                    cast_names = []
                    if cast:
                        sorted_cast = sorted(cast, key=lambda x: x.get('order', 999))
                        cast_names = [c.get('name', '').strip() for c in sorted_cast[:5] if c.get('name')]
                    
                    # Get director
                    director = ''
                    if crew:
                        directors = [c.get('name', '').strip() for c in crew 
                                   if c.get('job') == 'Director' and c.get('name')]
                        director = directors[0] if directors else ''
                    
                    # Check if movie already exists
                    if Movie.objects.filter(tmdb_id=tmdb_id).exists():
                        print(f"⚠️  Row {row_num}: Skipped (already exists): {title}")
                        skip_count += 1
                        continue
                    
                    # Create movie
                    movie = Movie.objects.create(
                        tmdb_id=tmdb_id,
                        title=title,
                        description=overview,
                        release_date=release_date,
                        duration=runtime,
                        poster_url=poster_url,
                        director=director,
                        cast=cast_names,
                    )
                    
                    # Set genres (many-to-many relationship)
                    if genre_objs:
                        movie.genres.set(genre_objs)
                    
                    print(f"✅ Row {row_num}: Added: {title} ({release_date.year if release_date else 'Unknown year'})")
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ Row {row_num}: Error processing movie: {e}")
                    if 'title' in locals():
                        print(f"   Title: {title}")
                    error_count += 1
                    continue

except FileNotFoundError:
    print(f"Movies file not found: {movies_path}")
except Exception as e:
    print(f"Fatal error processing movies: {e}")

# === Summary ===
print("\n" + "="*50)
print("IMPORT SUMMARY")
print("="*50)
print(f"Successfully imported: {success_count} movies")
print(f"Skipped (already exist): {skip_count} movies")
print(f"Errors encountered: {error_count} movies")
print(f"Total genres created: {Genre.objects.count()}")
print(f"Total movies in database: {Movie.objects.count()}")
print("="*50)
