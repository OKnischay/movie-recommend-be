# movies/tmdb_utils.py

import requests
import time
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from .models import Movie, Genre
import logging

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
LARGE_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w780"

# Rate limiting
RATE_LIMIT_DELAY = 0.25  # 4 requests per second (TMDB limit is 40/10 seconds)

def get_tmdb_headers():
    """Get headers for TMDB API requests"""
    return {
        "Authorization": f"Bearer {settings.TMDB_API_KEY}",
        "Accept": "application/json"
    }

def make_tmdb_request(url, params=None, use_cache=True, cache_timeout=3600):
    """
    Make a request to TMDB API with caching and rate limiting
    """
    if params is None:
        params = {}
    
    # Add API key to params
    params['api_key'] = settings.TMDB_API_KEY
    
    # Create cache key
    cache_key = f"tmdb_{hash(url + str(sorted(params.items())))}"
    
    # Check cache first
    if use_cache:
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response
    
    # Rate limiting
    time.sleep(RATE_LIMIT_DELAY)
    
    try:
        response = requests.get(url, params=params, headers=get_tmdb_headers())
        response.raise_for_status()
        
        json_data = response.json()
        
        # Cache the response
        if use_cache:
            cache.set(cache_key, json_data, cache_timeout)
        
        return json_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"TMDB API request failed: {url} - {str(e)}")
        raise

def get_movie_details(tmdb_id):
    """Get detailed movie information from TMDB"""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {"language": "en-US"}
    return make_tmdb_request(url, params)

def get_movie_credits(tmdb_id):
    """Get movie credits (cast and crew) from TMDB"""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits"
    return make_tmdb_request(url)

def get_movie_videos(tmdb_id):
    """Get movie videos (trailers, etc.) from TMDB"""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/videos"
    return make_tmdb_request(url)

def get_movie_images(tmdb_id):
    """Get movie images (posters, backdrops) from TMDB"""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/images"
    return make_tmdb_request(url)

def search_movies(query, page=1):
    """Search for movies on TMDB"""
    url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "query": query,
        "page": page,
        "language": "en-US"
    }
    return make_tmdb_request(url, params)

def get_popular_movies(page=1):
    """Get popular movies from TMDB"""
    url = f"{TMDB_BASE_URL}/movie/popular"
    params = {
        "page": page,
        "language": "en-US"
    }
    return make_tmdb_request(url, params)

def get_trending_movies(time_window="week"):
    """Get trending movies from TMDB"""
    url = f"{TMDB_BASE_URL}/trending/movie/{time_window}"
    params = {"language": "en-US"}
    return make_tmdb_request(url, params)

def extract_trailer_url(video_data):
    """Extract YouTube trailer URL from video data"""
    videos = video_data.get("results", [])
    
    # Prioritize official trailers
    for video in videos:
        if (video.get("type") == "Trailer" and 
            video.get("site") == "YouTube" and 
            video.get("official", False)):
            return f"https://www.youtube.com/watch?v={video['key']}"
    
    # Fall back to any trailer
    for video in videos:
        if video.get("type") == "Trailer" and video.get("site") == "YouTube":
            return f"https://www.youtube.com/watch?v={video['key']}"
    
    return ""

def extract_director(crew):
    """Extract director name from crew data"""
    for member in crew:
        if member.get("job") == "Director":
            return member.get("name", "")
    return ""

def extract_cast_names(cast, limit=10):
    """Extract actor names from cast data"""
    return [member.get("name") for member in cast[:limit] if member.get("name")]

def get_best_poster_url(movie_data, images_data=None):
    """Get the best available poster URL"""
    poster_path = movie_data.get("poster_path")
    
    if poster_path:
        return f"{IMAGE_BASE_URL}{poster_path}"
    
    # If no poster in main data, try images endpoint
    if images_data:
        posters = images_data.get("posters", [])
        if posters:
            # Get the highest rated English poster, or first available
            english_posters = [p for p in posters if p.get("iso_639_1") == "en"]
            if english_posters:
                best_poster = max(english_posters, key=lambda x: x.get("vote_average", 0))
            else:
                best_poster = posters[0]
            
            return f"{IMAGE_BASE_URL}{best_poster['file_path']}"
    
    return ""

def get_backdrop_url(movie_data):
    """Get backdrop URL if available"""
    backdrop_path = movie_data.get("backdrop_path")
    if backdrop_path:
        return f"{LARGE_IMAGE_BASE_URL}{backdrop_path}"
    return ""

@transaction.atomic
def sync_movie_by_tmdb_id(tmdb_id):
    """
    Sync a movie from TMDB to local database
    Enhanced with better error handling and additional data
    """
    try:
        # Get all movie data
        details = get_movie_details(tmdb_id)
        credits = get_movie_credits(tmdb_id)
        videos = get_movie_videos(tmdb_id)
        images = get_movie_images(tmdb_id)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch movie data from TMDB (ID: {tmdb_id}): {str(e)}")
        return None
    
    try:
        # Handle genres
        genre_objs = []
        for genre in details.get("genres", []):
            genre_obj, created = Genre.objects.get_or_create(
                name=genre["name"]
            )
            genre_objs.append(genre_obj)
        
        # Extract movie data
        director = extract_director(credits.get("crew", []))
        cast = extract_cast_names(credits.get("cast", []))
        trailer_url = extract_trailer_url(videos)
        poster_url = get_best_poster_url(details, images)
        backdrop_url = get_backdrop_url(details)
        
        # Handle release date
        release_date = details.get("release_date")
        if release_date == "":
            release_date = None
        
        # Create or update movie
        movie, created = Movie.objects.update_or_create(
            tmdb_id=tmdb_id,
            defaults={
                "title": details.get("title", ""),
                "description": details.get("overview", ""),
                "release_date": release_date,
                "duration": details.get("runtime", 0),
                "poster_url": poster_url,
                "trailer_url": trailer_url,
                "imdb_id": details.get("imdb_id", ""),
                "director": director,
                "cast": cast,
            }
        )
        
        # Set genres
        movie.genres.set(genre_objs)
        movie.save()
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} movie: {movie.title} (TMDB ID: {tmdb_id})")
        
        return movie
        
    except Exception as e:
        logger.error(f"Failed to save movie to database (TMDB ID: {tmdb_id}): {str(e)}")
        return None

def bulk_import_popular_movies(pages=5, skip_existing=False, batch_size=10):
    """
    Import popular movies from TMDB in bulk
    """
    imported_count = 0
    failed_count = 0
    
    for page in range(1, pages + 1):
        try:
            popular_movies = get_popular_movies(page)
            
            for movie_data in popular_movies.get("results", []):
                tmdb_id = movie_data.get("id")
                if tmdb_id:
                    # Check if movie already exists
                    if skip_existing and Movie.objects.filter(tmdb_id=tmdb_id).exists():
                        continue
                    movie = sync_movie_by_tmdb_id(tmdb_id)
                    if movie:
                        imported_count += 1
                    else:
                        failed_count += 1
                    
                    # Add delay to respect rate limits
                    time.sleep(RATE_LIMIT_DELAY)
    
        except Exception as e:
            logger.error(f"Failed to import popular movies page {page}: {str(e)}")
            failed_count += len(popular_movies.get("results", []))
    
    logger.info(f"Bulk import completed: {imported_count} imported, {failed_count} failed")
    return {"imported": imported_count, "failed": failed_count}

def search_and_import_movie(query):
    """
    Search for a movie and import the first result
    """
    try:
        search_results = search_movies(query)
        results = search_results.get("results", [])
        
        if not results:
            return None, "No movies found"
        
        first_result = results[0]
        tmdb_id = first_result.get("id")
        
        if Movie.objects.filter(tmdb_id=tmdb_id).exists():
            movie = Movie.objects.get(tmdb_id=tmdb_id)
            return movie, "Movie already exists in database"
        
        movie = sync_movie_by_tmdb_id(tmdb_id)
        if movie:
            return movie, "Movie imported successfully"
        else:
            return None, "Failed to import movie"
            
    except Exception as e:
        logger.error(f"Error searching and importing movie '{query}': {str(e)}")
        return None, f"Error: {str(e)}"