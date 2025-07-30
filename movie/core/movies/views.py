# movies/views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.core.cache import cache

from users.models import CustomUser
from .models import Movie, Genre, UserRating, UserPreference, UserReview, Watchlist, WatchHistory, Favorite
from .serializers import (
    FavoriteMovieDetailSerializer, FavoriteSerializer, MovieSerializer, GenreSerializer, RecommendMovieSerializer, 
    UserRatingSerializer, UserPreferenceSerializer, UserReviewSerializer, WatchHistorySerializer, WatchlistSerializer
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
# @permission_classes([permissions.IsAuthenticated])
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

        synced_movies = []

        for item in recommendations:
            if isinstance(item, Movie):
                synced_movies.append(item)
                continue

            tmdb_id = item.get("id")
            if not tmdb_id:
                continue

            movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
            if not movie:
                movie = sync_movie_by_tmdb_id(tmdb_id)

            if movie:
                synced_movies.append(movie)

        # Batch user-specific data
        if user:
            watchlist_ids = set(
                Watchlist.objects.filter(user=user, movie__in=synced_movies).values_list("movie_id", flat=True)
            )
            favorite_ids = set(
                Favorite.objects.filter(user=user, movie__in=synced_movies).values_list("movie_id", flat=True)
            )
            ratings = {
                r.movie_id: r.rating
                for r in UserRating.objects.filter(user=user, movie__in=synced_movies)
            }

            for movie in synced_movies:
                movie._is_in_watchlist = movie.id in watchlist_ids
                movie._is_favorite = movie.id in favorite_ids
                movie._user_rating = ratings.get(movie.id)

        serializer = RecommendMovieSerializer(synced_movies, many=True, context={'request': request})
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
def similar_movies_view(request, tmdb_id):
    """Get movies similar to a specific movie"""
    try:
        limit = int(request.query_params.get('limit', 10))
        
        service = RecommendationService(request.user if request.user.is_authenticated else None)
        similar = service.get_similar_movies(tmdb_id, limit=limit)
        
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

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def user_watchlist_view(request):
#     """Get all watchlist for current user"""
#     print("Authenticated user:", request.user)
#     watchlist = Watchlist.objects.filter(user=request.user).select_related('movie')
#     print("Found watchlist items:", watchlist.count())
#     serializer = WatchlistSerializer(watchlist, many=True)
#     return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_watchlist_view(request):
    """Get all watchlist for current user"""
    print("Authenticated user:", request.user)
    watchlist = Watchlist.objects.filter(user=request.user).select_related('movie')
    print("Found watchlist items:", watchlist.count())
    serializer = WatchlistSerializer(watchlist, many=True, context={'request': request})
    return Response(serializer.data)



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
        serializer = WatchlistSerializer(watchlist, many=True, context={"request": request}) 
        return Response(serializer.data)


# @api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
# def add_to_watch_history(request, tmdb_id):
#     try:
#         movie = Movie.objects.get(tmdb_id=tmdb_id)
#     except Movie.DoesNotExist:
#         return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
#     completion_percentage = request.data.get("completion_percentage", 100)

#     obj, created = WatchHistory.objects.update_or_create(
#         user=request.user,
#         movie=movie,
#         defaults={"completion_percentage": completion_percentage}
#     )

#     return Response({
#         "message": "Watch history updated" if not created else "Watch history added",
#         "completion_percentage": obj.completion_percentage
#     }, status=status.HTTP_200_OK)

# class WatchHistoryListView(generics.ListAPIView):
#     serializer_class = WatchHistorySerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return WatchHistory.objects.filter(user=self.request.user).select_related('movie').order_by('-watched_at')


# class WatchHistoryDetailView(generics.RetrieveUpdateDestroyAPIView):
#     serializer_class = WatchHistorySerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return WatchHistory.objects.filter(user=self.request.user)

@api_view(['POST', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def watch_history_by_tmdb(request, tmdb_id):
    try:
        movie = Movie.objects.get(tmdb_id=tmdb_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    if request.method == 'POST':
        completion_percentage = request.data.get("completion_percentage", 100)
        obj, created = WatchHistory.objects.update_or_create(
            user=user,
            movie=movie,
            defaults={"completion_percentage": completion_percentage}
        )
        return Response({
            "message": "Watch history updated" if not created else "Watch history added",
            "completion_percentage": obj.completion_percentage
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        try:
            watch_entry = WatchHistory.objects.get(user=user, movie=movie)
        except WatchHistory.DoesNotExist:
            return Response({'error': 'Watch history not found'}, status=status.HTTP_400_BAD_REQUEST)

        completion_percentage = request.data.get("completion_percentage", 100)
        watch_entry.completion_percentage = completion_percentage
        watch_entry.save()
        return Response({
            "message": "Watch history updated",
            "completion_percentage": watch_entry.completion_percentage
        }, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        try:
            watch_entry = WatchHistory.objects.get(user=user, movie=movie)
            watch_entry.delete()
            return Response({"message": "Watch history deleted"}, status=status.HTTP_200_OK)
        except WatchHistory.DoesNotExist:
            return Response({'error': 'Watch history not found'}, status=status.HTTP_400_BAD_REQUEST)
        

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def watchhistory_list(request):
#     queryset = WatchHistory.objects.filter(user=request.user).select_related('movie').order_by('-watched_at')
#     serializer = WatchHistorySerializer(queryset, many=True),
#     return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def watchhistory_list(request):
    queryset = WatchHistory.objects.filter(user=request.user).select_related('movie').order_by('-watched_at')
    serializer = WatchHistorySerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data)


def get_movie(movie_id):
    try:
        return Movie.objects.get(tmdb_id=movie_id)
    except Movie.DoesNotExist:
        try:
            return Movie.objects.get(id=movie_id)
        except Movie.DoesNotExist:
            return None

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def movie_reviews(request, tmdb_id):
    movie = get_movie(tmdb_id)
    if not movie:
        return Response({'detail': 'Movie not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if request.method == 'GET':
        reviews = UserReview.objects.filter(movie=movie).select_related('user', 'movie').order_by('-created_at')
        serializer = UserReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        if UserReview.objects.filter(user=request.user, movie=movie).exists():
            return Response({'detail': 'You have already reviewed this movie'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = UserReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, movie=movie)
            # Changed from 201 to 200 per your request
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def movie_reviews_public(request, tmdb_id):
    movie = get_movie(tmdb_id)
    if not movie:
        return Response({'detail': 'Movie not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    reviews = UserReview.objects.filter(movie=movie).select_related('user', 'movie').order_by('-created_at')
    serializer = UserReviewSerializer(reviews, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def user_movie_review(request, tmdb_id):
#     movie = get_movie(tmdb_id)
#     if not movie:
#         return Response({'detail': 'Movie not found'}, status=status.HTTP_400_BAD_REQUEST)
    
#     try:
#         review = UserReview.objects.get(user=request.user, movie=movie)
#     except UserReview.DoesNotExist:
#         return Response({'detail': 'Review not found'}, status=status.HTTP_400_BAD_REQUEST)
    
#     serializer = UserReviewSerializer(review)
#     return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_movie_review(request, tmdb_id):
    movie = get_movie(tmdb_id)
    if not movie:
        return Response({'detail': 'Movie not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        review = UserReview.objects.get(user=request.user, movie=movie)
        serializer = UserReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except UserReview.DoesNotExist:
        # Return empty JSON object instead of error
        return Response({}, status=status.HTTP_200_OK)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def review_detail(request, pk):
    try:
        review = UserReview.objects.get(pk=pk, user=request.user)
    except UserReview.DoesNotExist:
        return Response({'detail': 'Review not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if request.method == 'GET':
        serializer = UserReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = UserReviewSerializer(review, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        review.delete()
        return Response({'detail': 'Review deleted successfully'}, status=status.HTTP_200_OK)


