# movies/views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.core.cache import cache

from users.models import CustomUser
from .models import Movie, Genre, UserRating, UserPreference, Watchlist, WatchHistory, Favorite
from .serializers import (
    FavoriteMovieDetailSerializer, FavoriteSerializer, MovieSerializer, GenreSerializer, 
    UserRatingSerializer, UserPreferenceSerializer, WatchlistSerializer
)
from .services import RecommendationService
from .tmdb_utils import (
    TMDB_GENRE_MAP, sync_movie_by_tmdb_id, search_movies, get_popular_movies,
    get_trending_movies, search_and_import_movie
)
import logging
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def import_tmdb_movie_view(request):
    """Import a movie from TMDB by ID"""
    tmdb_id = request.data.get("tmdb_id")
    if not tmdb_id:
        return Response({"error": "tmdb_id is required"}, status=400)
    
    try:
        # Check if movie already exists
        existing_movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
        if existing_movie:
            serializer = MovieSerializer(existing_movie, context={'request': request})
            return Response({
                "message": "Movie already exists in database",
                "movie": serializer.data
            }, status=200)
        
        movie = sync_movie_by_tmdb_id(tmdb_id)
        if not movie:
            return Response({"error": "Failed to fetch movie from TMDB"}, status=500)

        serializer = MovieSerializer(movie, context={'request': request})
        return Response({
            "message": "Movie imported successfully",
            "movie": serializer.data
        }, status=201)
        
    except Exception as e:
        logger.error(f"Error importing movie {tmdb_id}: {str(e)}")
        return Response({"error": "Internal server error"}, status=500)
    
@api_view(['GET'])
def search_tmdb_movies_view(request):
    """Search movies on TMDB without importing"""
    query = request.query_params.get('query', '').strip()
    page = int(request.query_params.get('page', 1))
    
    if not query:
        return Response({"error": "Query parameter is required"}, status=400)
    
    try:
        # Check cache first
        cache_key = f"tmdb_search_{query}_{page}"
        cached_results = cache.get(cache_key)
        if cached_results:
            return Response(cached_results)
        
        results = search_movies(query, page)
        
        # Add local availability info
        for movie in results.get('results', []):
            tmdb_id = movie.get('id')
            if tmdb_id:
                movie['locally_available'] = Movie.objects.filter(tmdb_id=tmdb_id).exists()
        
        # Cache results for 1 hour
        cache.set(cache_key, results, 3600)
        
        return Response(results)
        
    except Exception as e:
        logger.error(f"Error searching TMDB: {str(e)}")
        return Response({"error": "Failed to search movies"}, status=500)
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def search_and_import_view(request):
    """Search for a movie and import the first result"""
    query = request.data.get('query', '').strip()
    
    if not query:
        return Response({"error": "Query is required"}, status=400)
    
    try:
        movie, message = search_and_import_movie(query)
        
        if movie:
            serializer = MovieSerializer(movie, context={'request': request})
            return Response({
                "message": message,
                "movie": serializer.data
            }, status=200 if "already exists" in message else 201)
        else:
            return Response({"error": message}, status=404)
            
    except Exception as e:
        logger.error(f"Error searching and importing '{query}': {str(e)}")
        return Response({"error": "Internal server error"}, status=500)
    
@api_view(['GET'])
def popular_movies_view(request):
    """Get popular movies from TMDB (cached)"""
    page = int(request.query_params.get('page', 1))
    
    try:
        cache_key = f"popular_movies_{page}"
        cached_results = cache.get(cache_key)
        if cached_results:
            return Response(cached_results)
        
        results = get_popular_movies(page)
        
        # Add local availability info
        for movie in results.get('results', []):
            tmdb_id = movie.get('id')
            if tmdb_id:
                movie['locally_available'] = Movie.objects.filter(tmdb_id=tmdb_id).exists()
        
        # Cache for 2 hours
        cache.set(cache_key, results, 7200)
        
        return Response(results)
        
    except Exception as e:
        logger.error(f"Error fetching popular movies: {str(e)}")
        return Response({"error": "Failed to fetch popular movies"}, status=500)
class MoviePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class MovieListView(generics.ListAPIView):
    serializer_class = MovieSerializer
    pagination_class = MoviePagination
    
    def get_queryset(self):
        queryset = Movie.objects.all().select_related().prefetch_related('genres')
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(director__icontains=search) |
                Q(cast__icontains=search)
            )
        
        # Genre filtering
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genres__name__icontains=genre)
        
        # Year filtering
        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(release_date__year=year)
        
        # Rating filtering
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(average_rating__gte=float(min_rating))
            except ValueError:
                pass
        
        # Sort options
        sort_by = self.request.query_params.get('sort', 'newest')
        if sort_by == 'rating':
            queryset = queryset.order_by('-average_rating', '-rating_count')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-rating_count', '-average_rating')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('release_date')
        elif sort_by == 'alphabetical':
            queryset = queryset.order_by('title')
        else:  # newest
            queryset = queryset.order_by('-created_at')
        
        return queryset
class MovieDetailView(generics.RetrieveAPIView):
    queryset = Movie.objects.all().select_related().prefetch_related('genres', 'user_ratings')
    serializer_class = MovieSerializer

class GenreListView(generics.ListAPIView):
    serializer_class = GenreSerializer
    
    def get_queryset(self):
        # Cache genres for 1 hour
        cache_key = "all_genres"
        cached_genres = cache.get(cache_key)
        if cached_genres is None:
            queryset = Genre.objects.all().order_by('name')
            cache.set(cache_key, list(queryset), 3600)
            return queryset
        return cached_genres

@api_view(['GET'])
def recommendations_view(request):
    """Get personalized movie recommendations"""
    try:
        user = request.user if request.user.is_authenticated else None
        limit = int(request.query_params.get('limit', 20))
        
        service = RecommendationService(user)
        recommendations = service.get_recommendations(limit=limit)
        
        serializer = MovieSerializer(recommendations, many=True, context={'request': request})
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return Response({"error": "Failed to get recommendations"}, status=500)
    
@api_view(['GET'])
def movie_by_tmdb_id_view(request, tmdb_id):
    try:
        movie = Movie.objects.get(tmdb_id=tmdb_id)
        serializer = MovieSerializer(movie, context={'request': request})
        return Response(serializer.data)
    except Movie.DoesNotExist:
        return Response({"detail": "Movie not found"}, status=404)

@api_view(['GET'])
def trending_movies_view(request):
    """Get trending movies from local database or TMDB"""
    try:
        # Try to get from local database first
        user = request.user if request.user.is_authenticated else None
        service = RecommendationService(user)
        trending = service.get_trending_movies(limit=10)
        
        if trending:
            serializer = MovieSerializer(trending, many=True, context={'request': request})
            return Response(serializer.data)
        
        # Fall back to TMDB trending
        cache_key = "tmdb_trending_movies"
        cached_trending = cache.get(cache_key)
        if cached_trending:
            return Response(cached_trending)

        trending_data = get_trending_movies()

        # Add local availability info
        for movie in trending_data.get('results', []):
            tmdb_id = movie.get('id')
            if tmdb_id:
                movie['locally_available'] = Movie.objects.filter(tmdb_id=tmdb_id).exists()

            genre_ids = movie.get("genre_ids", [])
            movie["genres"] = [
                {"id": gid, "name": TMDB_GENRE_MAP.get(gid, "Unknown")}
                for gid in genre_ids
            ]

        # Cache for 1 hour
        cache.set(cache_key, trending_data, 3600)

        return Response(trending_data)
        
    except Exception as e:
        logger.error(f"Error getting trending movies: {str(e)}")
        return Response({"error": "Failed to get trending movies"}, status=500)

@api_view(['GET'])
def similar_movies_view(request, movie_id):
    """Get movies similar to a specific movie"""
    try:
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(request.user if request.user.is_authenticated else None)
        similar = service.get_similar_movies(movie_id, limit=limit)
        
        serializer = MovieSerializer(similar, many=True, context={'request': request})
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting similar movies: {str(e)}")
        return Response({"error": "Failed to get similar movies"}, status=500)

# class UserRatingListCreateView(generics.ListCreateAPIView):
#     serializer_class = UserRatingSerializer
#     permission_classes = [permissions.IsAuthenticated]
    
#     def get_queryset(self):
#         return UserRating.objects.filter(user=self.request.user).order_by('-created_at')
class UserRatingListCreateView(generics.ListCreateAPIView):
    serializer_class = UserRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserRating.objects.filter(user=self.request.user).order_by('-created_at')
    
    def post(self, request, *args, **kwargs):
        print(f"Request data: {request.data}")
        print(f"User: {request.user}")
        print(f"User authenticated: {request.user.is_authenticated}")
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        print(f"Performing create with serializer data: {serializer.validated_data}")
        serializer.save()

class UserRatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserRating.objects.filter(user=self.request.user)

class UserPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        preference, created = UserPreference.objects.get_or_create(user=self.request.user)
        return preference
    
@api_view(['GET'])
def movie_stats_view(request):
    """Get movie database statistics"""
    try:
        stats = {
            'total_movies': Movie.objects.count(),
            'total_genres': Genre.objects.count(),
            'total_ratings': UserRating.objects.count(),
            'movies_with_posters': Movie.objects.exclude(poster_url='').count(),
            'movies_with_trailers': Movie.objects.exclude(trailer_url='').count(),
            'latest_movie': Movie.objects.order_by('-created_at').first().title if Movie.objects.exists() else None,
        }
        return Response(stats)
    except Exception as e:
        logger.error(f"Error getting movie stats: {str(e)}")
        return Response({"error": "Failed to get statistics"}, status=500)

@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def watchlist_view(request, tmdb_id):
    """Add or remove movie from watchlist"""
    try:
        movie = Movie.objects.get(tmdb_id=tmdb_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'POST':
        watchlist_item, created = Watchlist.objects.get_or_create(
            user=request.user, movie=movie
        )
        if created:
            return Response({'message': 'Added to watchlist'}, status=status.HTTP_201_CREATED)
        return Response({'message': 'Already in watchlist'}, status=status.HTTP_200_OK)
    
    elif request.method == 'DELETE':
        deleted_count, _ = Watchlist.objects.filter(
            user=request.user, movie=movie
        ).delete()
        if deleted_count:
            return Response({'message': 'Removed from watchlist'}, status=status.HTTP_200_OK)
        return Response({'message': 'Not in watchlist'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def watchlist_status_view(request):
    """Check if movie is in user's watchlist"""
    tmdb_id = request.query_params.get('movie_id')  # frontend still sends `movie_id`, which is tmdb_id
    if not tmdb_id:
        return Response({'error': 'movie_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        movie = Movie.objects.get(tmdb_id=tmdb_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
    is_in_watchlist = Watchlist.objects.filter(
        user=request.user, movie=movie
    ).exists()
    
    return Response({'is_in_watchlist': is_in_watchlist}, status=status.HTTP_200_OK)


@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def favorite_view(request, tmdb_id):
    """Add or remove movie from favorites"""
    try:
        movie = Movie.objects.get(tmdb_id=tmdb_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'POST':
        favorite, created = Favorite.objects.get_or_create(
            user=request.user, movie=movie
        )
        if created:
            serializer = FavoriteSerializer(favorite)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'message': 'Movie already in favorites'}, status=status.HTTP_200_OK)
    
    elif request.method == 'DELETE':
        deleted, _ = Favorite.objects.filter(
            user=request.user, movie=movie
        ).delete()
        if deleted:
            return Response({'message': 'Removed from favorites'}, status=status.HTTP_200_OK)
        return Response({'message': 'Movie not in favorites'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def favorite_status_view(request):
    """Check if movie is in user's favorites"""
    tmdb_id = request.query_params.get('movie_id')
    if not tmdb_id:
        return Response({'error': 'movie_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        movie = Movie.objects.get(tmdb_id=tmdb_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
    is_favorite = Favorite.objects.filter(
        user=request.user, movie=movie
    ).exists()
    
    return Response({'is_favorite': is_favorite}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_favorites_view(request):
    """Get all favorites for current user"""
    favorites = Favorite.objects.filter(user=request.user).select_related('movie')
    serializer = FavoriteSerializer(favorites, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_favorite_movies_view(request, user_id):
    """Get all favorite movies (with details) for a specific user ID"""
    user = get_object_or_404(CustomUser, id=user_id)
    favorites = Favorite.objects.filter(user=user).select_related('movie')
    serializer = FavoriteMovieDetailSerializer(favorites, many=True, context={'request': request})
    return Response(serializer.data)

class UserWatchlistAPIView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        watchlist = Watchlist.objects.filter(user=user)
        serializer = WatchlistSerializer(watchlist, many=True, context={"request": request})  # ✅ FIXED
        return Response(serializer.data)
