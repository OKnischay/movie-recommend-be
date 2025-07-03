# # movies/services.py
# from django.db.models import Q, Avg, Count, F
# from users.models import CustomUser as User
# from .models import Movie, UserRating, UserPreference, Genre, WatchHistory
# import numpy as np
# from datetime import datetime, timedelta



# class RecommendationService:
#     def __init__(self, user):
#         self.user = user
#         self.preferences = self.get_or_create_preferences()
    
#     def get_or_create_preferences(self):
#         """Get or create user preferences"""
#         preferences, created = UserPreference.objects.get_or_create(user=self.user)
#         return preferences
    
#     def get_recommendations(self, limit=20):
#         """Main recommendation method using hybrid approach"""
#         # Get movies user hasn't rated or watched
#         excluded_movies = set()
        
#         # Exclude rated movies
#         rated_movies = UserRating.objects.filter(user=self.user).values_list('movie_id', flat=True)
#         excluded_movies.update(rated_movies)
        
#         # Exclude watched movies
#         watched_movies = WatchHistory.objects.filter(user=self.user).values_list('movie_id', flat=True)
#         excluded_movies.update(watched_movies)
        
#         # Get candidate movies
#         candidate_movies = Movie.objects.exclude(id__in=excluded_movies)
        
#         # Apply different recommendation strategies
#         collaborative_recs = self.collaborative_filtering(candidate_movies, limit//2)
#         content_recs = self.content_based_filtering(candidate_movies, limit//2)
        
#         # Combine and deduplicate
#         combined_recs = self.combine_recommendations(collaborative_recs, content_recs, limit)
        
#         return combined_recs
    
#     def collaborative_filtering(self, candidate_movies, limit):
#         """Find similar users and recommend their liked movies"""
#         if not UserRating.objects.filter(user=self.user).exists():
#             return []
        
#         # Find users with similar taste
#         user_ratings = UserRating.objects.filter(user=self.user)
#         similar_users = self.find_similar_users(user_ratings)
        
#         if not similar_users:
#             return []
        
#         # Get highly rated movies from similar users
#         similar_user_ratings = UserRating.objects.filter(
#             user__in=similar_users,
#             rating__gte=4.0,
#             movie__in=candidate_movies
#         ).select_related('movie').order_by('-rating', '-movie__average_rating')
        
#         return [rating.movie for rating in similar_user_ratings[:limit]]
    
#     def find_similar_users(self, user_ratings, threshold=0.3):
#         """Find users with similar movie ratings using Pearson correlation"""
#         user_movie_ratings = {rating.movie_id: rating.rating for rating in user_ratings}
        
#         if len(user_movie_ratings) < 3:  # Need at least 3 common movies
#             return []
        
#         similar_users = []
        
#         # Get other users who rated same movies
#         other_users = User.objects.filter(
#             ratings__movie_id__in=user_movie_ratings.keys()
#         ).annotate(
#             common_movies=Count('ratings__movie', filter=Q(ratings__movie_id__in=user_movie_ratings.keys()))
#         ).filter(common_movies__gte=3).exclude(id=self.user.id)
        
#         for other_user in other_users:
#             other_ratings = {
#                 rating.movie_id: rating.rating 
#                 for rating in UserRating.objects.filter(
#                     user=other_user, 
#                     movie_id__in=user_movie_ratings.keys()
#                 )
#             }
            
#             # Calculate Pearson correlation
#             correlation = self.calculate_correlation(user_movie_ratings, other_ratings)
            
#             if correlation > threshold:
#                 similar_users.append(other_user)
        
#         return similar_users
    
#     def calculate_correlation(self, ratings1, ratings2):
#         """Calculate Pearson correlation between two rating dictionaries"""
#         common_movies = set(ratings1.keys()) & set(ratings2.keys())
        
#         if len(common_movies) < 3:
#             return 0
        
#         ratings1_values = [ratings1[movie] for movie in common_movies]
#         ratings2_values = [ratings2[movie] for movie in common_movies]
        
#         correlation_matrix = np.corrcoef(ratings1_values, ratings2_values)
#         correlation = correlation_matrix[0, 1]
        
#         return correlation if not np.isnan(correlation) else 0
    
#     def content_based_filtering(self, candidate_movies, limit):
#         """Recommend movies based on user's genre preferences and rating history"""
#         # Get user's favorite genres from preferences and rating history
#         favorite_genres = set(self.preferences.favorite_genres.all())
#         disliked_genres = set(self.preferences.disliked_genres.all())
        
#         # Analyze user's rating history for genre preferences
#         if UserRating.objects.filter(user=self.user).exists():
#             liked_movie_genres = Genre.objects.filter(
#                 movies__user_ratings__user=self.user,
#                 movies__user_ratings__rating__gte=4.0
#             ).annotate(
#                 avg_rating=Avg('movies__user_ratings__rating')
#             ).order_by('-avg_rating')
            
#             favorite_genres.update(liked_movie_genres[:5])
        
#         # Score movies based on content similarity
#         scored_movies = []
        
#         for movie in candidate_movies.prefetch_related('genres'):
#             score = self.calculate_content_score(movie, favorite_genres, disliked_genres)
#             if score > 0:
#                 scored_movies.append((movie, score))
        
#         # Sort by score and return top movies
#         scored_movies.sort(key=lambda x: x[1], reverse=True)
#         return [movie for movie, score in scored_movies[:limit]]
    
#     def calculate_content_score(self, movie, favorite_genres, disliked_genres):
#         """Calculate content-based score for a movie"""
#         score = 0
#         movie_genres = set(movie.genres.all())
        
#         # Genre matching
#         genre_score = 0
#         if movie_genres & favorite_genres:
#             genre_score = len(movie_genres & favorite_genres) / len(movie_genres)
        
#         if movie_genres & disliked_genres:
#             genre_score -= len(movie_genres & disliked_genres) / len(movie_genres)
        
#         # Movie quality score (average rating and popularity)
#         quality_score = float(movie.average_rating) / 5.0 if movie.average_rating else 0
#         popularity_score = min(movie.rating_count / 1000, 1.0)  # Normalize popularity
        
#         # Recency bonus for newer movies
#         days_since_release = (datetime.now().date() - movie.release_date).days
#         recency_score = max(0, 1 - (days_since_release / 3650))  # 10-year decay
        
#         # Weighted combination
#         score = (
#             genre_score * self.preferences.genre_weight +
#             quality_score * self.preferences.rating_weight +
#             popularity_score * self.preferences.popularity_weight +
#             recency_score * self.preferences.recency_weight
#         )
        
#         return score
    
#     def combine_recommendations(self, collaborative_recs, content_recs, limit):
#         """Combine and deduplicate recommendations from different methods"""
#         seen_movies = set()
#         combined = []
        
#         # Interleave recommendations to maintain diversity
#         max_length = max(len(collaborative_recs), len(content_recs))
        
#         for i in range(max_length):
#             # Add collaborative filtering recommendation
#             if i < len(collaborative_recs) and collaborative_recs[i].id not in seen_movies:
#                 combined.append(collaborative_recs[i])
#                 seen_movies.add(collaborative_recs[i].id)
                
#                 if len(combined) >= limit:
#                     break
            
#             # Add content-based recommendation
#             if i < len(content_recs) and content_recs[i].id not in seen_movies:
#                 combined.append(content_recs[i])
#                 seen_movies.add(content_recs[i].id)
                
#                 if len(combined) >= limit:
#                     break
        
#         return combined
    
#     def get_trending_movies(self, limit=10):
#         """Get currently trending movies based on recent ratings"""
#         thirty_days_ago = datetime.now() - timedelta(days=30)
        
#         trending = Movie.objects.filter(
#             user_ratings__created_at__gte=thirty_days_ago
#         ).annotate(
#             recent_ratings_count=Count('user_ratings'),
#             recent_avg_rating=Avg('user_ratings__rating')
#         ).filter(
#             recent_ratings_count__gte=5,
#             recent_avg_rating__gte=3.5
#         ).order_by('-recent_ratings_count', '-recent_avg_rating')
        
#         return trending[:limit]
    
#     def get_similar_movies(self, movie_id, limit=10):
#         """Get movies similar to a specific movie"""
#         try:
#             movie = Movie.objects.get(id=movie_id)
#         except Movie.DoesNotExist:
#             return []
        
#         # Find movies with similar genres
#         similar_movies = Movie.objects.filter(
#             genres__in=movie.genres.all()
#         ).exclude(id=movie_id).annotate(
#             genre_overlap=Count('genres', filter=Q(genres__in=movie.genres.all()))
#         ).order_by('-genre_overlap', '-average_rating')
        
#         return similar_movies[:limit]

# movies/services.py
from django.db.models import Q, Avg, Count, F
from users.models import CustomUser as User
from .models import Movie, UserRating, UserPreference, Genre, WatchHistory
import numpy as np
from datetime import datetime, timedelta

class RecommendationService:
    def __init__(self, user):
        self.user = user
        self.preferences = self.get_or_create_preferences() if user and user.is_authenticated else None
    
    def get_or_create_preferences(self):
        """Get or create user preferences"""
        if not self.user or not self.user.is_authenticated:
            return None
        preferences, created = UserPreference.objects.get_or_create(user=self.user)
        return preferences
    
    def get_recommendations(self, limit=20):
        """Main recommendation method using hybrid approach"""
        # If no authenticated user, return popular movies
        if not self.user or not self.user.is_authenticated:
            return self.get_popular_movies(limit)
        
        # Get movies user hasn't rated or watched
        excluded_movies = set()
        
        # Exclude rated movies
        rated_movies = UserRating.objects.filter(user=self.user).values_list('movie_id', flat=True)
        excluded_movies.update(rated_movies)
        
        # Exclude watched movies
        watched_movies = WatchHistory.objects.filter(user=self.user).values_list('movie_id', flat=True)
        excluded_movies.update(watched_movies)
        
        # Get candidate movies
        candidate_movies = Movie.objects.exclude(id__in=excluded_movies)
        
        # Apply different recommendation strategies
        collaborative_recs = self.collaborative_filtering(candidate_movies, limit//2)
        content_recs = self.content_based_filtering(candidate_movies, limit//2)
        
        # Combine and deduplicate
        combined_recs = self.combine_recommendations(collaborative_recs, content_recs, limit)
        
        # If we don't have enough recommendations, fill with popular movies
        if len(combined_recs) < limit:
            popular_movies = self.get_popular_movies(limit - len(combined_recs), excluded_movies)
            combined_recs.extend(popular_movies)
        
        return combined_recs
    
    def get_popular_movies(self, limit, excluded_movies=None):
        """Get popular movies for anonymous users or as fallback"""
        queryset = Movie.objects.filter(
            average_rating__gte=3.5,
            rating_count__gte=10
        ).order_by('-average_rating', '-rating_count')
        
        if excluded_movies:
            queryset = queryset.exclude(id__in=excluded_movies)
        
        return list(queryset[:limit])
    
    def collaborative_filtering(self, candidate_movies, limit):
        """Find similar users and recommend their liked movies"""
        if not self.user or not self.user.is_authenticated:
            return []
            
        if not UserRating.objects.filter(user=self.user).exists():
            return []
        
        # Find users with similar taste
        user_ratings = UserRating.objects.filter(user=self.user)
        similar_users = self.find_similar_users(user_ratings)
        
        if not similar_users:
            return []
        
        # Get highly rated movies from similar users
        similar_user_ratings = UserRating.objects.filter(
            user__in=similar_users,
            rating__gte=4.0,
            movie__in=candidate_movies
        ).select_related('movie').order_by('-rating', '-movie__average_rating')
        
        return [rating.movie for rating in similar_user_ratings[:limit]]
    
    def find_similar_users(self, user_ratings, threshold=0.3):
        """Find users with similar movie ratings using Pearson correlation"""
        user_movie_ratings = {rating.movie_id: rating.rating for rating in user_ratings}
        
        if len(user_movie_ratings) < 3:  # Need at least 3 common movies
            return []
        
        similar_users = []
        
        # Get other users who rated same movies
        other_users = User.objects.filter(
            ratings__movie_id__in=user_movie_ratings.keys()
        ).annotate(
            common_movies=Count('ratings__movie', filter=Q(ratings__movie_id__in=user_movie_ratings.keys()))
        ).filter(common_movies__gte=3).exclude(id=self.user.id)
        
        for other_user in other_users:
            other_ratings = {
                rating.movie_id: rating.rating 
                for rating in UserRating.objects.filter(
                    user=other_user, 
                    movie_id__in=user_movie_ratings.keys()
                )
            }
            
            # Calculate Pearson correlation
            correlation = self.calculate_correlation(user_movie_ratings, other_ratings)
            
            if correlation > threshold:
                similar_users.append(other_user)
        
        return similar_users
    
    def calculate_correlation(self, ratings1, ratings2):
        """Calculate Pearson correlation between two rating dictionaries"""
        common_movies = set(ratings1.keys()) & set(ratings2.keys())
        
        if len(common_movies) < 3:
            return 0
        
        ratings1_values = [ratings1[movie] for movie in common_movies]
        ratings2_values = [ratings2[movie] for movie in common_movies]
        
        correlation_matrix = np.corrcoef(ratings1_values, ratings2_values)
        correlation = correlation_matrix[0, 1]
        
        return correlation if not np.isnan(correlation) else 0
    
    def content_based_filtering(self, candidate_movies, limit):
        """Recommend movies based on user's genre preferences and rating history"""
        if not self.user or not self.user.is_authenticated or not self.preferences:
            return []
        
        # Get user's favorite genres from preferences and rating history
        favorite_genres = set(self.preferences.favorite_genres.all())
        disliked_genres = set(self.preferences.disliked_genres.all())
        
        # Analyze user's rating history for genre preferences
        if UserRating.objects.filter(user=self.user).exists():
            liked_movie_genres = Genre.objects.filter(
                movies__user_ratings__user=self.user,
                movies__user_ratings__rating__gte=4.0
            ).annotate(
                avg_rating=Avg('movies__user_ratings__rating')
            ).order_by('-avg_rating')
            
            favorite_genres.update(liked_movie_genres[:5])
        
        # Score movies based on content similarity
        scored_movies = []
        
        for movie in candidate_movies.prefetch_related('genres'):
            score = self.calculate_content_score(movie, favorite_genres, disliked_genres)
            if score > 0:
                scored_movies.append((movie, score))
        
        # Sort by score and return top movies
        scored_movies.sort(key=lambda x: x[1], reverse=True)
        return [movie for movie, score in scored_movies[:limit]]
    
    def calculate_content_score(self, movie, favorite_genres, disliked_genres):
        """Calculate content-based score for a movie"""
        if not self.preferences:
            return 0
            
        score = 0
        movie_genres = set(movie.genres.all())
        
        # Genre matching
        genre_score = 0
        if movie_genres & favorite_genres:
            genre_score = len(movie_genres & favorite_genres) / len(movie_genres)
        
        if movie_genres & disliked_genres:
            genre_score -= len(movie_genres & disliked_genres) / len(movie_genres)
        
        # Movie quality score (average rating and popularity)
        quality_score = float(movie.average_rating) / 5.0 if movie.average_rating else 0
        popularity_score = min(movie.rating_count / 1000, 1.0)  # Normalize popularity
        
        # Recency bonus for newer movies
        days_since_release = (datetime.now().date() - movie.release_date).days
        recency_score = max(0, 1 - (days_since_release / 3650))  # 10-year decay
        
        # Weighted combination
        score = (
            genre_score * self.preferences.genre_weight +
            quality_score * self.preferences.rating_weight +
            popularity_score * self.preferences.popularity_weight +
            recency_score * self.preferences.recency_weight
        )
        
        return score
    
    def combine_recommendations(self, collaborative_recs, content_recs, limit):
        """Combine and deduplicate recommendations from different methods"""
        seen_movies = set()
        combined = []
        
        # Interleave recommendations to maintain diversity
        max_length = max(len(collaborative_recs), len(content_recs))
        
        for i in range(max_length):
            # Add collaborative filtering recommendation
            if i < len(collaborative_recs) and collaborative_recs[i].id not in seen_movies:
                combined.append(collaborative_recs[i])
                seen_movies.add(collaborative_recs[i].id)
                
                if len(combined) >= limit:
                    break
            
            # Add content-based recommendation
            if i < len(content_recs) and content_recs[i].id not in seen_movies:
                combined.append(content_recs[i])
                seen_movies.add(content_recs[i].id)
                
                if len(combined) >= limit:
                    break
        
        return combined
    
    def get_trending_movies(self, limit=10):
        """Get currently trending movies based on recent ratings"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        trending = Movie.objects.filter(
            user_ratings__created_at__gte=thirty_days_ago
        ).annotate(
            recent_ratings_count=Count('user_ratings'),
            recent_avg_rating=Avg('user_ratings__rating')
        ).filter(
            recent_ratings_count__gte=5,
            recent_avg_rating__gte=3.5
        ).order_by('-recent_ratings_count', '-recent_avg_rating')
        
        return trending[:limit]
    
    def get_similar_movies(self, movie_id, limit=10):
        """Get movies similar to a specific movie"""
        try:
            movie = Movie.objects.get(id=movie_id)
        except Movie.DoesNotExist:
            return []
        
        # Find movies with similar genres
        similar_movies = Movie.objects.filter(
            genres__in=movie.genres.all()
        ).exclude(id=movie_id).annotate(
            genre_overlap=Count('genres', filter=Q(genres__in=movie.genres.all()))
        ).order_by('-genre_overlap', '-average_rating')
        
        return similar_movies[:limit]