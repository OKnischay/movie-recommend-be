# from rest_framework import generics, status, permissions
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
# from rest_framework.pagination import PageNumberPagination
# from django.db.models import Q
# from .models import Movie, Genre, UserRating, UserPreference, Watchlist, WatchHistory
# from .serializers import MovieSerializer, GenreSerializer, UserRatingSerializer, UserPreferenceSerializer
# from .services import RecommendationService

# class MoviePagination(PageNumberPagination):
#     page_size = 20
#     page_size_query_param = 'page_size'
#     max_page_size = 100

# class MovieListView(generics.ListAPIView):
#     serializer_class = MovieSerializer
#     pagination_class = MoviePagination
    
#     def get_queryset(self):
#         queryset = Movie.objects.all().order_by('-created_at')
        
#         # Search functionality
#         search = self.request.query_params.get('search')
#         if search:
#             queryset = queryset.filter(
#                 Q(title__icontains=search) |
#                 Q(description__icontains=search) |
#                 Q(director__icontains=search)
#             )
        
#         # Genre filtering
#         genre = self.request.query_params.get('genre')
#         if genre:
#             queryset = queryset.filter(genres__name__icontains=genre)
        
#         # Sort options
#         sort_by = self.request.query_params.get('sort', 'newest')
#         if sort_by == 'rating':
#             queryset = queryset.order_by('-average_rating', '-rating_count')
#         elif sort_by == 'popular':
#             queryset = queryset.order_by('-rating_count', '-average_rating')
#         elif sort_by == 'oldest':
#             queryset = queryset.order_by('release_date')
        
#         return queryset

# class MovieDetailView(generics.RetrieveAPIView):
#     queryset = Movie.objects.all()
#     serializer_class = MovieSerializer

# class GenreListView(generics.ListAPIView):
#     queryset = Genre.objects.all().order_by('name')
#     serializer_class = GenreSerializer

# @api_view(['GET'])
# # @permission_classes([permissions.IsAuthenticated])
# def recommendations_view(request):
#     """Get personalized movie recommendations"""
#     service = RecommendationService(request.user)
#     recommendations = service.get_recommendations(limit=20)
#     serializer = MovieSerializer(recommendations, many=True, context={'request': request})
#     return Response(serializer.data)

# @api_view(['GET'])
# def trending_movies_view(request):
#     """Get trending movies"""
#     service = RecommendationService(request.user if request.user.is_authenticated else None)
#     trending = service.get_trending_movies(limit=10)
#     serializer = MovieSerializer(trending, many=True, context={'request': request})
#     return Response(serializer.data)

# @api_view(['GET'])
# def similar_movies_view(request, movie_id):
#     """Get movies similar to a specific movie"""
#     service = RecommendationService(request.user if request.user.is_authenticated else None)
#     similar = service.get_similar_movies(movie_id, limit=10)
#     serializer = MovieSerializer(similar, many=True, context={'request': request})
#     return Response(serializer.data)

# class UserRatingListCreateView(generics.ListCreateAPIView):
#     serializer_class = UserRatingSerializer
#     # permission_classes = [permissions.IsAuthenticated]
    
#     def get_queryset(self):
#         return UserRating.objects.filter(user=self.request.user).order_by('-created_at')

# class UserRatingDetailView(generics.RetrieveUpdateDestroyAPIView):
#     serializer_class = UserRatingSerializer
#     # permission_classes = [permissions.IsAuthenticated]
    
#     def get_queryset(self):
#         return UserRating.objects.filter(user=self.request.user)

# class UserPreferenceView(generics.RetrieveUpdateAPIView):
#     serializer_class = UserPreferenceSerializer
#     # permission_classes = [permissions.IsAuthenticated]
    
#     def get_object(self):
#         preference, created = UserPreference.objects.get_or_create(user=self.request.user)
#         return preference

# @api_view(['POST', 'DELETE'])
# # @permission_classes([permissions.IsAuthenticated])
# def watchlist_view(request, movie_id):
#     """Add or remove movie from watchlist"""
#     try:
#         movie = Movie.objects.get(id=movie_id)
#     except Movie.DoesNotExist:
#         return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
#     if request.method == 'POST':
#         watchlist_item, created = Watchlist.objects.get_or_create(
#             user=request.user, movie=movie
#         )
#         if created:
#             return Response({'message': 'Added to watchlist'}, status=status.HTTP_201_CREATED)
#         else:
#             return Response({'message': 'Already in watchlist'}, status=status.HTTP_200_OK)
    
#     elif request.method == 'DELETE':
#         deleted_count, _ = Watchlist.objects.filter(
#             user=request.user, movie=movie
#         ).delete()
#         if deleted_count:
#             return Response({'message': 'Removed from watchlist'}, status=status.HTTP_200_OK)
#         else:
#             return Response({'message': 'Not in watchlist'}, status=status.HTTP_404_NOT_FOUND)

# @api_view(['GET'])
# # @permission_classes([permissions.IsAuthenticated])
# def user_watchlist_view(request):
#     """Get user's watchlist"""
#     watchlist_items = Watchlist.objects.filter(user=request.user).select_related('movie')
#     movies = [item.movie for item in watchlist_items]
#     serializer = MovieSerializer(movies, many=True, context={'request': request})
#     return Response(serializer.data)

# @api_view(['POST'])
# # @permission_classes([permissions.IsAuthenticated])
# def mark_watched_view(request, movie_id):
#     """Mark a movie as watched"""
#     try:
#         movie = Movie.objects.get(id=movie_id)
#     except Movie.DoesNotExist:
#         return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
#     completion_percentage = request.data.get('completion_percentage', 100.0)
    
#     watch_history, created = WatchHistory.objects.get_or_create(
#         user=request.user,
#         movie=movie,
#         defaults={'completion_percentage': completion_percentage}
#     )
    
#     if not created:
#         watch_history.completion_percentage = completion_percentage
#         watch_history.save()
    
#     return Response({'message': 'Marked as watched'}, status=status.HTTP_201_CREATED)

# movies/views.py
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Movie, Genre, UserRating, UserPreference, Watchlist, WatchHistory, Favorite
from .serializers import FavoriteSerializer, MovieSerializer, GenreSerializer, UserRatingSerializer, UserPreferenceSerializer
from .services import RecommendationService

class MoviePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class MovieListView(generics.ListAPIView):
    serializer_class = MovieSerializer
    pagination_class = MoviePagination
    
    def get_queryset(self):
        queryset = Movie.objects.all().order_by('-created_at')
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(director__icontains=search)
            )
        
        # Genre filtering
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genres__name__icontains=genre)
        
        # Sort options
        sort_by = self.request.query_params.get('sort', 'newest')
        if sort_by == 'rating':
            queryset = queryset.order_by('-average_rating', '-rating_count')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-rating_count', '-average_rating')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('release_date')
        
        return queryset

class MovieDetailView(generics.RetrieveAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

class GenreListView(generics.ListAPIView):
    queryset = Genre.objects.all().order_by('name')
    serializer_class = GenreSerializer

@api_view(['GET'])
def recommendations_view(request):
    """Get personalized movie recommendations or popular movies for anonymous users"""
    # For authenticated users, get personalized recommendations
    # For anonymous users, get popular movies
    user = request.user if request.user.is_authenticated else None
    service = RecommendationService(user)
    recommendations = service.get_recommendations(limit=20)
    serializer = MovieSerializer(recommendations, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def trending_movies_view(request):
    """Get trending movies"""
    service = RecommendationService(request.user if request.user.is_authenticated else None)
    trending = service.get_trending_movies(limit=10)
    serializer = MovieSerializer(trending, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def similar_movies_view(request, movie_id):
    """Get movies similar to a specific movie"""
    service = RecommendationService(request.user if request.user.is_authenticated else None)
    similar = service.get_similar_movies(movie_id, limit=10)
    serializer = MovieSerializer(similar, many=True, context={'request': request})
    return Response(serializer.data)

class UserRatingListCreateView(generics.ListCreateAPIView):
    serializer_class = UserRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserRating.objects.filter(user=self.request.user).order_by('-created_at')

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

@api_view(['POST', 'DELETE'])
# @permission_classes([IsAuthenticated])
def watchlist_view(request, movie_id):
    """Add or remove movie from watchlist"""
    try:
        movie = Movie.objects.get(id=movie_id)
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
# @permission_classes([IsAuthenticated])
def watchlist_status_view(request):
    """Check if movie is in user's watchlist"""
    movie_id = request.query_params.get('movie_id')
    if not movie_id:
        return Response({'error': 'movie_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        movie = Movie.objects.get(id=movie_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
    is_in_watchlist = Watchlist.objects.filter(
        user=request.user, movie=movie
    ).exists()
    
    return Response({'is_in_watchlist': is_in_watchlist}, status=status.HTTP_200_OK)
@api_view(['POST', 'DELETE'])
# @permission_classes([IsAuthenticated])
def favorite_view(request, movie_id):
    """Add or remove movie from favorites"""
    try:
        movie = Movie.objects.get(id=movie_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'POST':
        favorite, created = Favorite.objects.get_or_create(
            user=request.user, 
            movie=movie,
            defaults={'user': request.user, 'movie': movie}
        )
        if created:
            serializer = FavoriteSerializer(favorite)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'message': 'Movie already in favorites'}, status=status.HTTP_200_OK)
    
    elif request.method == 'DELETE':
        deleted, _ = Favorite.objects.filter(
            user=request.user,
            movie=movie
        ).delete()
        if deleted:
            return Response({'message': 'Removed from favorites'}, status=status.HTTP_200_OK)
        return Response({'message': 'Movie not in favorites'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def favorite_status_view(request):
    """Check if movie is in user's favorites"""
    movie_id = request.query_params.get('movie_id')
    if not movie_id:
        return Response({'error': 'movie_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        movie = Movie.objects.get(id=movie_id)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    
    is_favorite = Favorite.objects.filter(
        user=request.user,
        movie=movie
    ).exists()
    
    return Response({'is_favorite': is_favorite}, status=status.HTTP_200_OK)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def user_favorites_view(request):
    """Get all favorites for current user"""
    favorites = Favorite.objects.filter(user=request.user).select_related('movie')
    serializer = FavoriteSerializer(favorites, many=True)
    return Response(serializer.data)