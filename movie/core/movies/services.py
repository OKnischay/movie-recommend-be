# # movies/services.py
# from django.db.models import Q, Avg, Count, F
# from users.models import CustomUser as User
# from .models import Movie, UserRating, UserPreference, Genre, WatchHistory
# import numpy as np
# from datetime import datetime, timedelta

# class RecommendationService:
#     def __init__(self, user):
#         self.user = user
#         self.preferences = self.get_or_create_preferences() if user and user.is_authenticated else None

#     def get_or_create_preferences(self):
#         """Get or create user preferences"""
#         if not self.user or not self.user.is_authenticated:
#             return None
#         preferences, created = UserPreference.objects.get_or_create(user=self.user)
#         return preferences

#     def get_recommendations(self, limit=20):
#         """Main recommendation method using hybrid approach"""
#         # If no authenticated user, return popular movies
#         if not self.user or not self.user.is_authenticated:
#             return self.get_popular_movies(limit)

#         excluded_movies = set()

#         # Exclude rated movies
#         rated_movies = UserRating.objects.filter(user=self.user).values_list('movie_id', flat=True)
#         excluded_movies.update(rated_movies)

#         watched_movies = WatchHistory.objects.filter(user=self.user).values_list('movie_id', flat=True)
#         excluded_movies.update(watched_movies)

#         candidate_movies = Movie.objects.exclude(id__in=excluded_movies)

#         # Apply different recommendation strategies
#         collaborative_recs = self.collaborative_filtering(candidate_movies, limit//2)
#         content_recs = self.content_based_filtering(candidate_movies, limit//2)

#         # Combine and deduplicate
#         combined_recs = self.combine_recommendations(collaborative_recs, content_recs, limit)

#         # If we don't have enough recommendations, fill with popular movies
#         if len(combined_recs) < limit:
#             popular_movies = self.get_popular_movies(limit - len(combined_recs), excluded_movies)
#             combined_recs.extend(popular_movies)

#         return combined_recs

#     def get_popular_movies(self, limit, excluded_movies=None):
#         """Get popular movies for anonymous users or as fallback"""
#         queryset = Movie.objects.filter(
#             average_rating__gte=3.5,
#             rating_count__gte=10
#         ).order_by('-average_rating', '-rating_count')

#         if excluded_movies:
#             queryset = queryset.exclude(id__in=excluded_movies)

#         return list(queryset[:limit])

#     def collaborative_filtering(self, candidate_movies, limit):
#         """Find similar users and recommend their liked movies"""
#         if not self.user or not self.user.is_authenticated:
#             return []

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
#         if not self.user or not self.user.is_authenticated or not self.preferences:
#             return []

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
#         if not self.preferences:
#             return 0

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

#     # def get_similar_movies(self, movie_id, limit=10):
#     #     """Get movies similar to a specific movie"""
#     #     try:
#     #         movie = Movie.objects.get(id=movie_id)
#     #     except Movie.DoesNotExist:
#     #         return []

#     #     # Find movies with similar genres
#     #     similar_movies = Movie.objects.filter(
#     #         genres__in=movie.genres.all()
#     #     ).exclude(id=movie_id).annotate(
#     #         genre_overlap=Count('genres', filter=Q(genres__in=movie.genres.all()))
#     #     ).order_by('-genre_overlap', '-average_rating')

#     #     return similar_movies[:limit]

#     def get_similar_movies(self, tmdb_id, limit=10):
#         """Get movies similar to a specific movie"""
#         try:
#             movie = Movie.objects.get(tmdb_id=tmdb_id)
#             print(f"Movie: {movie.title}")
#             print(f"Movie genres: {list(movie.genres.all())}")

#             if not movie.genres.exists():
#                 print("No genres found for this movie!")
#                 return []

#         except Movie.DoesNotExist:
#             print(f"Movie with id {tmdb_id} does not exist")
#             return []

#         # Find movies with similar genres
#         similar_movies = Movie.objects.filter(
#             genres__in=movie.genres.all()
#         ).exclude(tmdb_id=tmdb_id).annotate(
#             genre_overlap=Count('genres', filter=Q(genres__in=movie.genres.all()))
#         ).order_by('-genre_overlap', '-average_rating')

#         print(f"Found {similar_movies.count()} similar movies")
#         return similar_movies[:limit]


# movies/services.py
from django.db.models import Q, Avg, Count, F
from users.models import CustomUser as User
from .models import Movie, UserRating, UserPreference, Genre, WatchHistory
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import csr_matrix
import re
import logging

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, user):
        self.user = user
        self.preferences = (
            self.get_or_create_preferences() if user and user.is_authenticated else None
        )

    def get_or_create_preferences(self):
        """Get or create user preferences"""
        if not self.user or not self.user.is_authenticated:
            return None
        preferences, created = UserPreference.objects.get_or_create(user=self.user)
        return preferences

    # def get_recommendations(self, limit=20):
    #     """Main recommendation method using proper hybrid approach"""
    #     if not self.user or not self.user.is_authenticated:
    #         return self.get_popular_movies(limit)

    #     excluded_movies = set()

    #     # Exclude rated and watched movies
    #     rated_movies = UserRating.objects.filter(user=self.user).values_list(
    #         "movie_id", flat=True
    #     )
    #     excluded_movies.update(rated_movies)
    #     watched_movies = WatchHistory.objects.filter(user=self.user).values_list(
    #         "movie_id", flat=True
    #     )
    #     excluded_movies.update(watched_movies)

    #     candidate_movies = Movie.objects.exclude(id__in=excluded_movies)

    #     # Get recommendations from both methods
    #     cf_recommendations = self.collaborative_filtering_improved(
    #         candidate_movies, limit
    #     )
    #     cbf_recommendations = self.content_based_filtering_improved(
    #         candidate_movies, limit
    #     )

    #     # Combine using weighted hybrid approach
    #     combined_recs = self.hybrid_combination(
    #         cf_recommendations, cbf_recommendations, limit
    #     )

    #     # Fill with popular movies if needed
    #     if len(combined_recs) < limit:
    #         popular_movies = self.get_popular_movies(
    #             limit - len(combined_recs), excluded_movies
    #         )
    #         combined_recs.extend(popular_movies)

    #     return combined_recs[:limit]

    def get_recommendations(self, limit=20):
        """Main recommendation method using proper hybrid approach"""
        if not self.user or not self.user.is_authenticated:
            return self.get_popular_movies(limit)

        excluded_movies = set()

        # Exclude rated and watched movies
        rated_movies = UserRating.objects.filter(user=self.user).values_list(
            "movie_id", flat=True
        )
        excluded_movies.update(rated_movies)
        watched_movies = WatchHistory.objects.filter(user=self.user).values_list(
            "movie_id", flat=True
        )
        excluded_movies.update(watched_movies)

        # Start with base candidate movies
        candidate_movies = Movie.objects.exclude(id__in=excluded_movies)
        
        # CRITICAL: Apply disliked genre filter BEFORE any recommendation processing
        candidate_movies = self.filter_disliked_genres(candidate_movies)
        
        print(f"Candidate movies after filtering disliked genres: {candidate_movies.count()}")

        # Get recommendations from both methods
        cf_recommendations = self.collaborative_filtering_improved(
            candidate_movies, limit
        )
        cbf_recommendations = self.content_based_filtering_improved(
            candidate_movies, limit
        )

        # Combine using weighted hybrid approach
        combined_recs = self.hybrid_combination(
            cf_recommendations, cbf_recommendations, limit
        )

        # Fill with popular movies if needed (also apply genre filter)
        if len(combined_recs) < limit:
            popular_candidates = Movie.objects.filter(rating_count__gte=1)
            if excluded_movies:
                popular_candidates = popular_candidates.exclude(id__in=excluded_movies)
            
            # Apply disliked genre filter to popular movies too
            popular_candidates = self.filter_disliked_genres(popular_candidates)
            
            popular_movies = list(
                popular_candidates.order_by("-average_rating", "-rating_count")
                [:limit - len(combined_recs)]
            )
            combined_recs.extend(popular_movies)

        return combined_recs[:limit]

    def collaborative_filtering_improved(self, candidate_movies, limit):
        """
        Improved Collaborative Filtering using matrix factorization and user-item similarity
        """
        try:
            # Build user-item rating matrix
            ratings_data = list(
                UserRating.objects.all().values("user_id", "movie_id", "rating")
            )

            if len(ratings_data) < 10:  # Not enough data for CF
                return []

            # Create DataFrame
            df = pd.DataFrame(ratings_data)

            # Create user-item matrix
            user_item_matrix = df.pivot(
                index="user_id", columns="movie_id", values="rating"
            ).fillna(0)

            # Convert to sparse matrix for efficiency
            sparse_matrix = csr_matrix(user_item_matrix.values)

            # Apply SVD for matrix factorization
            svd = TruncatedSVD(
                n_components=min(50, sparse_matrix.shape[1] - 1), random_state=42
            )
            user_factors = svd.fit_transform(sparse_matrix)
            item_factors = svd.components_.T

            # Get current user's factor vector
            if self.user.id not in user_item_matrix.index:
                return []

            user_idx = list(user_item_matrix.index).index(self.user.id)
            user_vector = user_factors[user_idx].reshape(1, -1)

            # Calculate predicted ratings for all movies
            predicted_ratings = user_vector.dot(item_factors.T).flatten()

            # Get movie recommendations
            movie_ids = user_item_matrix.columns.tolist()
            movie_scores = list(zip(movie_ids, predicted_ratings))

            # Filter for candidate movies and sort by predicted rating
            candidate_ids = set(candidate_movies.values_list("id", flat=True))
            filtered_scores = [
                (mid, score) for mid, score in movie_scores if mid in candidate_ids
            ]
            filtered_scores.sort(key=lambda x: x[1], reverse=True)

            # Get movie objects
            recommended_movie_ids = [mid for mid, _ in filtered_scores[:limit]]
            movies = Movie.objects.filter(id__in=recommended_movie_ids)

            # Preserve order
            movie_dict = {m.id: m for m in movies}
            return [
                movie_dict[mid] for mid in recommended_movie_ids if mid in movie_dict
            ]

        except Exception as e:
            logger.error(f"Error in collaborative filtering: {str(e)}")
            return []

    def content_based_filtering_improved(self, candidate_movies, limit):
        """
        Content-Based Filtering using TF-IDF and multiple features
        """
        try:
            # Get user's rating history for profile building
            user_ratings = (
                UserRating.objects.filter(user=self.user, rating__gte=8.0)
                .select_related("movie")
                .prefetch_related("movie__genres")
            )

            if not user_ratings.exists():
                return []

            # Build user profile from liked movies
            user_profile = self.build_user_content_profile(user_ratings)

            # Get candidate movies with features
            candidate_movies_list = list(candidate_movies.prefetch_related("genres"))

            if not candidate_movies_list:
                return []

            # Calculate content similarity scores
            scored_movies = []
            for movie in candidate_movies_list:
                similarity_score = self.calculate_content_similarity(
                    movie, user_profile
                )
                if similarity_score > 0:
                    scored_movies.append((movie, similarity_score))

            # Sort by similarity score
            scored_movies.sort(key=lambda x: x[1], reverse=True)

            return [movie for movie, _ in scored_movies[:limit]]

        except Exception as e:
            logger.error(f"Error in content-based filtering: {str(e)}")
            return []

    def build_user_content_profile(self, user_ratings):
        """Build user profile from liked movies using TF-IDF"""
        # Collect features from liked movies
        liked_movies = [rating.movie for rating in user_ratings]

        # Extract text features
        movie_texts = []
        for movie in liked_movies:
            # Combine multiple text features
            text_features = []

            # Genres
            genres = [genre.name for genre in movie.genres.all()]
            text_features.extend(genres)

            # Director
            if movie.director:
                text_features.append(f"director_{movie.director.replace(' ', '_')}")

            # Cast (first 5 actors)
            if movie.cast:
                cast_list = (
                    movie.cast[:5]
                    if isinstance(movie.cast, list)
                    else movie.cast.split(",")[:5]
                )
                for actor in cast_list:
                    if actor.strip():
                        text_features.append(f"actor_{actor.strip().replace(' ', '_')}")

            # Description keywords (simple extraction)
            if movie.description:
                # Extract important keywords from description
                keywords = self.extract_keywords(movie.description)
                text_features.extend(keywords)

            movie_texts.append(" ".join(text_features))

        # Create TF-IDF vectors
        if movie_texts:
            vectorizer = TfidfVectorizer(
                max_features=1000, stop_words="english", ngram_range=(1, 2)
            )
            tfidf_matrix = vectorizer.fit_transform(movie_texts)

            # Average the TF-IDF vectors to create user profile
            user_profile_vector = np.mean(tfidf_matrix.toarray(), axis=0)

            return {
                "vector": user_profile_vector,
                "vectorizer": vectorizer,
                "genres": self.get_preferred_genres(liked_movies),
                "directors": self.get_preferred_directors(liked_movies),
                "cast": self.get_preferred_cast(liked_movies),
            }

        return None

    def extract_keywords(self, text, max_keywords=10):
        """Extract important keywords from movie description"""
        # Simple keyword extraction
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())

        # Remove common words
        stop_words = {
            "movie",
            "film",
            "story",
            "when",
            "after",
            "with",
            "their",
            "they",
            "this",
            "that",
        }
        keywords = [w for w in words if w not in stop_words]

        # Return most frequent keywords
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1

        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]

    def get_preferred_genres(self, movies):
        """Get user's preferred genres with weights"""
        genre_counts = {}
        for movie in movies:
            for genre in movie.genres.all():
                genre_counts[genre.name] = genre_counts.get(genre.name, 0) + 1
        return genre_counts

    def get_preferred_directors(self, movies):
        """Get user's preferred directors with weights"""
        director_counts = {}
        for movie in movies:
            if movie.director:
                director_counts[movie.director] = (
                    director_counts.get(movie.director, 0) + 1
                )
        print(f"Director counts: {director_counts}")
        return director_counts

    def get_preferred_cast(self, movies):
        """Get user's preferred cast with weights"""
        cast_counts = {}
        for movie in movies:
            if movie.cast:
                cast_list = (
                    movie.cast[:5]
                    if isinstance(movie.cast, list)
                    else movie.cast.split(",")[:5]
                )
                for actor in cast_list:
                    actor = actor.strip()
                    if actor:
                        cast_counts[actor] = cast_counts.get(actor, 0) + 1
        print(f"Cast counts: {cast_counts}")
        return cast_counts

    # def calculate_content_similarity(self, movie, user_profile):
    #     """Calculate similarity between movie and user profile"""
    #     if not user_profile:
    #         return 0

    #     total_score = 0

    #     # Text-based similarity (TF-IDF)
    #     movie_text = self.create_movie_text_features(movie)
    #     if movie_text and user_profile.get("vectorizer"):
    #         try:
    #             movie_vector = (
    #                 user_profile["vectorizer"].transform([movie_text]).toarray()[0]
    #             )
    #             text_similarity = cosine_similarity(
    #                 [user_profile["vector"]], [movie_vector]
    #             )[0][0]
    #             total_score += text_similarity * 0.4
    #         except:
    #             pass

    #     # Genre similarity
    #     movie_genres = set(genre.name for genre in movie.genres.all())
    #     user_genres = set(user_profile.get("genres", {}).keys())
    #     if movie_genres and user_genres:
    #         genre_intersection = len(movie_genres & user_genres)
    #         genre_union = len(movie_genres | user_genres)
    #         genre_similarity = (
    #             genre_intersection / genre_union if genre_union > 0 else 0
    #         )
    #         total_score += genre_similarity * 0.3

    #     # Director similarity
    #     if movie.director and movie.director in user_profile.get("directors", {}):
    #         director_score = user_profile["directors"][movie.director] / sum(
    #             user_profile["directors"].values()
    #         )
    #         total_score += director_score * 0.2

    #     # Cast similarity
    #     if movie.cast:
    #         cast_list = (
    #             movie.cast[:5]
    #             if isinstance(movie.cast, list)
    #             else movie.cast.split(",")[:5]
    #         )
    #         cast_score = 0
    #         user_cast = user_profile.get("cast", {})
    #         if user_cast:
    #             for actor in cast_list:
    #                 actor = actor.strip()
    #                 if actor in user_cast:
    #                     cast_score += user_cast[actor] / sum(user_cast.values())
    #             total_score += (cast_score / len(cast_list)) * 0.1

    #     return total_score
    def calculate_content_similarity(self, movie, user_profile):
        """Calculate similarity between movie and user profile using content features"""
        if not user_profile or not self.preferences:
            return 0

        # BACKUP CHECK: Hard filter for disliked genres (should already be filtered, but double-check)
        movie_genres = set(genre.name for genre in movie.genres.all())
        disliked_genres = set(g.name for g in self.preferences.disliked_genres.all())
        
        # Case-insensitive check
        movie_genres_lower = set(g.lower() for g in movie_genres)
        disliked_genres_lower = set(g.lower() for g in disliked_genres)
        
        if movie_genres_lower & disliked_genres_lower:
            print(f"BLOCKED (backup check): {movie.title} contains disliked genres: {movie_genres & disliked_genres}")
            return 0  # Hard penalty

        total_score = 0

        # Get preference weights from UserPreference model
        genre_weight = self.preferences.genre_weight
        rating_weight = self.preferences.rating_weight
        popularity_weight = self.preferences.popularity_weight
        recency_weight = self.preferences.recency_weight

        # Normalize weights
        total_weight = genre_weight + rating_weight + popularity_weight + recency_weight
        if total_weight > 0:
            genre_weight /= total_weight
            rating_weight /= total_weight
            popularity_weight /= total_weight
            recency_weight /= total_weight

        # TF-IDF similarity
        movie_text = self.create_movie_text_features(movie)
        if movie_text and user_profile.get("vectorizer"):
            try:
                movie_vector = (
                    user_profile["vectorizer"].transform([movie_text]).toarray()[0]
                )
                text_similarity = cosine_similarity(
                    [user_profile["vector"]], [movie_vector]
                )[0][0]
                total_score += text_similarity * genre_weight
            except Exception:
                pass

        # Genre similarity with user preferences
        user_genres = set(user_profile.get("genres", {}).keys())
        favorite_genres = set(g.name for g in self.preferences.favorite_genres.all())

        if movie_genres and user_genres:
            genre_intersection = len(movie_genres & user_genres)
            genre_union = len(movie_genres | user_genres)
            genre_similarity = genre_intersection / genre_union if genre_union > 0 else 0
            total_score += genre_similarity * genre_weight * 0.7

        # Bonus for favorite genres
        if movie_genres & favorite_genres:
            total_score += 0.1 * genre_weight

        # Director similarity
        if movie.director and movie.director in user_profile.get("directors", {}):
            director_score = user_profile["directors"][movie.director] / sum(
                user_profile["directors"].values()
            )
            total_score += director_score * genre_weight * 0.2

        # Cast similarity
        cast_score = 0
        if movie.cast:
            cast_list = (
                movie.cast[:5]
                if isinstance(movie.cast, list)
                else movie.cast.split(",")[:5]
            )
            user_cast = user_profile.get("cast", {})
            match_count = 0
            for actor in cast_list:
                actor = actor.strip()
                if actor in user_cast:
                    cast_score += user_cast[actor] / sum(user_cast.values())
                    match_count += 1
            if match_count > 0:
                total_score += (cast_score / match_count) * genre_weight * 0.1

        # Popularity boost
        if movie.rating_count and movie.rating_count > 100:
            popularity_score = min(movie.rating_count / 1000, 1.0)
            total_score += popularity_score * popularity_weight

        # Recency boost
        if movie.release_date:
            try:
                release_date = datetime.strptime(movie.release_date, "%Y-%m-%d").date()
                days_since_release = (datetime.now().date() - release_date).days
                if days_since_release < 1000:
                    recency_score = (1000 - days_since_release) / 1000
                    total_score += recency_score * recency_weight
            except Exception:
                pass

        return total_score
                        
        

    def create_movie_text_features(self, movie):
        """Create text representation of movie for TF-IDF"""
        text_features = []

        # Genres
        genres = [genre.name for genre in movie.genres.all()]
        text_features.extend(genres)

        # Director
        if movie.director:
            text_features.append(f"director_{movie.director.replace(' ', '_')}")

        # Cast
        if movie.cast:
            cast_list = (
                movie.cast[:5]
                if isinstance(movie.cast, list)
                else movie.cast.split(",")[:5]
            )
            for actor in cast_list:
                if actor.strip():
                    text_features.append(f"actor_{actor.strip().replace(' ', '_')}")

        # Description keywords
        if movie.description:
            keywords = self.extract_keywords(movie.description)
            text_features.extend(keywords)

        return " ".join(text_features)

    def hybrid_combination(self, cf_recommendations, cbf_recommendations, limit):
        """
        Combine CF and CBF recommendations using weighted hybrid approach
        """
        # Weight parameters (can be tuned)
        cf_weight = 0.6
        cbf_weight = 0.4

        # Score movies from both approaches
        movie_scores = {}

        # Add CF scores
        for i, movie in enumerate(cf_recommendations):
            score = (
                (len(cf_recommendations) - i) / len(cf_recommendations)
                if cf_recommendations
                else 0
            )
            movie_scores[movie.id] = movie_scores.get(movie.id, 0) + score * cf_weight

        # Add CBF scores
        for i, movie in enumerate(cbf_recommendations):
            score = (
                (len(cbf_recommendations) - i) / len(cbf_recommendations)
                if cbf_recommendations
                else 0
            )
            movie_scores[movie.id] = movie_scores.get(movie.id, 0) + score * cbf_weight

        # Sort by combined score
        sorted_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)

        # Get movie objects
        movie_ids = [movie_id for movie_id, _ in sorted_movies[:limit]]
        movies = Movie.objects.filter(id__in=movie_ids)

        # Preserve order
        movie_dict = {m.id: m for m in movies}
        return [movie_dict[mid] for mid in movie_ids if mid in movie_dict]

    # def get_popular_movies(self, limit, excluded_movies=None):
    #     """Get popular movies for anonymous users or as fallback"""
    #     queryset = Movie.objects.filter(rating_count__gte=1).order_by(
    #         "-average_rating", "-rating_count"
    #     )

    #     if excluded_movies:
    #         queryset = queryset.exclude(id__in=excluded_movies)

    #     return list(queryset[:limit])

    def get_popular_movies(self, limit, excluded_movies=None):
        """Get popular movies for anonymous users or as fallback"""
        queryset = Movie.objects.filter(rating_count__gte=1).order_by(
            "-average_rating", "-rating_count"
        )

        if excluded_movies:
            queryset = queryset.exclude(id__in=excluded_movies)
        
        # Apply disliked genre filter for authenticated users
        if self.user and self.user.is_authenticated:
            queryset = self.filter_disliked_genres(queryset)

        return list(queryset[:limit])

    # def get_trending_movies(self, limit=10):
    #     """Get currently trending movies based on recent ratings"""
    #     thirty_days_ago = datetime.now() - timedelta(days=30)

    #     trending = (
    #         Movie.objects.filter(user_ratings__created_at__gte=thirty_days_ago)
    #         .annotate(
    #             recent_ratings_count=Count("user_ratings"),
    #             recent_avg_rating=Avg("user_ratings__rating"),
    #         )
    #         .filter(recent_ratings_count__gte=5, recent_avg_rating__gte=7.0)
    #         .order_by("-recent_ratings_count", "-recent_avg_rating")
    #     )
    #     for m in trending:
    #         print(f"Trending: {m.title} | Recent ratings: {m.recent_ratings_count} | Avg rating: {m.recent_avg_rating}")


    #     return trending[:limit]

    def get_trending_movies(self, limit=10):
        """Get currently trending movies based on recent ratings"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        trending = (
            Movie.objects.filter(user_ratings__created_at__gte=thirty_days_ago)
            .annotate(
                recent_ratings_count=Count("user_ratings"),
                recent_avg_rating=Avg("user_ratings__rating"),
            )
            .filter(recent_ratings_count__gte=5, recent_avg_rating__gte=7.0)
            .order_by("-recent_ratings_count", "-recent_avg_rating")
        )
        
        # Apply disliked genre filter for authenticated users
        if self.user and self.user.is_authenticated:
            trending = self.filter_disliked_genres(trending)
        
        for m in trending[:limit]:
            print(f"Trending: {m.title} | Recent ratings: {m.recent_ratings_count} | Avg rating: {m.recent_avg_rating}")

        return trending[:limit]

    # def get_similar_movies(self, tmdb_id, limit=10):
    #     """Get movies similar to a specific movie using content-based similarity"""
    #     try:
    #         movie = Movie.objects.get(tmdb_id=tmdb_id)

    #         # Create content profile for the target movie
    #         target_features = self.create_movie_text_features(movie)

    #         # Get all other movies
    #         other_movies = Movie.objects.exclude(tmdb_id=tmdb_id).prefetch_related(
    #             "genres"
    #         )

    #         # Calculate similarities
    #         similarities = []
    #         for other_movie in other_movies:
    #             other_features = self.create_movie_text_features(other_movie)

    #             if target_features and other_features:
    #                 # Use TF-IDF similarity
    #                 vectorizer = TfidfVectorizer(stop_words="english")
    #                 tfidf_matrix = vectorizer.fit_transform(
    #                     [target_features, other_features]
    #                 )
    #                 similarity = cosine_similarity(
    #                     tfidf_matrix[0:1], tfidf_matrix[1:2]
    #                 )[0][0]
    #                 similarities.append((other_movie, similarity))

    #         # Sort by similarity and return top movies
    #         similarities.sort(key=lambda x: x[1], reverse=True)
    #         return [movie for movie, _ in similarities[:limit]]

    #     except Movie.DoesNotExist:
    #         return []
    #     except Exception as e:
    #         logger.error(f"Error getting similar movies: {str(e)}")
    #         return []

    def get_similar_movies(self, tmdb_id, limit=10):
        """Get movies similar to a specific movie using content-based similarity"""
        try:
            movie = Movie.objects.get(tmdb_id=tmdb_id)

            # Create content profile for the target movie
            target_features = self.create_movie_text_features(movie)

            # Get all other movies and apply disliked genre filter
            other_movies = Movie.objects.exclude(tmdb_id=tmdb_id).prefetch_related("genres")
            
            # Apply disliked genre filter for authenticated users
            if self.user and self.user.is_authenticated:
                other_movies = self.filter_disliked_genres(other_movies)

            # Calculate similarities
            similarities = []
            for other_movie in other_movies:
                other_features = self.create_movie_text_features(other_movie)

                if target_features and other_features:
                    # Use TF-IDF similarity
                    vectorizer = TfidfVectorizer(stop_words="english")
                    tfidf_matrix = vectorizer.fit_transform(
                        [target_features, other_features]
                    )
                    similarity = cosine_similarity(
                        tfidf_matrix[0:1], tfidf_matrix[1:2]
                    )[0][0]
                    similarities.append((other_movie, similarity))

            # Sort by similarity and return top movies
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [movie for movie, _ in similarities[:limit]]

        except Movie.DoesNotExist:
            return []
        except Exception as e:
            logger.error(f"Error getting similar movies: {str(e)}")
            return []

    def update_user_preferences_from_behavior(self):
        """Automatically update user preferences based on rating behavior"""
        if not self.user or not self.user.is_authenticated:
            return
        
        # Get user's highly rated movies (8+ ratings)
        high_ratings = UserRating.objects.filter(
            user=self.user, 
            rating__gte=8.0
        ).select_related('movie').prefetch_related('movie__genres')
        
        if high_ratings.count() < 5:  # Need enough data
            return
        
        # Analyze genre preferences
        genre_counts = {}
        total_movies = high_ratings.count()
        
        for rating in high_ratings:
            for genre in rating.movie.genres.all():
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Update favorite genres (genres that appear in >40% of highly rated movies)
        favorite_threshold = total_movies * 0.4
        favorite_genres = [genre for genre, count in genre_counts.items() 
                        if count >= favorite_threshold]
        
        if favorite_genres:
            self.preferences.favorite_genres.set(favorite_genres)
        
        # Analyze and update disliked genres from low ratings
        low_ratings = UserRating.objects.filter(
            user=self.user, 
            rating__lte=4.0
        ).select_related('movie').prefetch_related('movie__genres')
        
        if low_ratings.count() >= 3:
            disliked_genre_counts = {}
            low_total = low_ratings.count()
            
            for rating in low_ratings:
                for genre in rating.movie.genres.all():
                    disliked_genre_counts[genre] = disliked_genre_counts.get(genre, 0) + 1
            
            # Genres that appear in >50% of low-rated movies
            disliked_threshold = low_total * 0.5
            disliked_genres = [genre for genre, count in disliked_genre_counts.items() 
                            if count >= disliked_threshold]
            
            if disliked_genres:
                self.preferences.disliked_genres.set(disliked_genres)

    # def get_diversity_boosted_recommendations(self, base_recommendations, diversity_factor=0.3):
    #     """Add diversity to recommendations to avoid filter bubbles"""
    #     if len(base_recommendations) <= 5:
    #         return base_recommendations
        
    #     # Keep top recommendations as is
    #     core_recs = base_recommendations[:int(len(base_recommendations) * (1 - diversity_factor))]
        
    #     # Add diverse recommendations for remaining slots
    #     diverse_slots = len(base_recommendations) - len(core_recs)
        
    #     # Get movies from different genres than core recommendations
    #     core_genres = set()
    #     for movie in core_recs:
    #         core_genres.update(genre.name for genre in movie.genres.all())
        
    #     # Find movies with different genres
    #     diverse_candidates = Movie.objects.exclude(
    #         id__in=[m.id for m in base_recommendations]
    #     ).prefetch_related('genres').filter(
    #         average_rating__gte=7.0
    #     )
        
    #     diverse_movies = []
    #     for movie in diverse_candidates:
    #         movie_genres = set(genre.name for genre in movie.genres.all())
    #         # If movie has genres not in core recommendations
    #         if not movie_genres.issubset(core_genres):
    #             diverse_movies.append(movie)
    #             if len(diverse_movies) >= diverse_slots:
    #                 break
        
    #     return list(core_recs) + diverse_movies

    def get_diversity_boosted_recommendations(self, base_recommendations, diversity_factor=0.3):
        """Add diversity to recommendations to avoid filter bubbles"""
        if len(base_recommendations) <= 5:
            return base_recommendations
        
        # Keep top recommendations as is
        core_recs = base_recommendations[:int(len(base_recommendations) * (1 - diversity_factor))]
        
        # Add diverse recommendations for remaining slots
        diverse_slots = len(base_recommendations) - len(core_recs)
        
        # Get movies from different genres than core recommendations
        core_genres = set()
        for movie in core_recs:
            core_genres.update(genre.name for genre in movie.genres.all())
        
        # Find movies with different genres
        diverse_candidates = Movie.objects.exclude(
            id__in=[m.id for m in base_recommendations]
        ).prefetch_related('genres').filter(
            average_rating__gte=7.0
        )
        
        # Apply disliked genre filter
        if self.user and self.user.is_authenticated:
            diverse_candidates = self.filter_disliked_genres(diverse_candidates)
        
        diverse_movies = []
        for movie in diverse_candidates:
            movie_genres = set(genre.name for genre in movie.genres.all())
            # If movie has genres not in core recommendations
            if not movie_genres.issubset(core_genres):
                diverse_movies.append(movie)
                if len(diverse_movies) >= diverse_slots:
                    break
        
        return list(core_recs) + diverse_movies


    # def get_contextual_recommendations(self, context="general", limit=20):
    #     """Get recommendations based on context (time of day, season, etc.)"""
    #     base_recs = self.get_recommendations(limit)
        
    #     if context == "weekend":
    #         # Prefer longer, more engaging movies for weekends
    #         weekend_boost = Movie.objects.filter(
    #             runtime__gte=120,  # 2+ hours
    #             id__in=[m.id for m in base_recs]
    #         )
    #         return list(weekend_boost) + [m for m in base_recs if m not in weekend_boost]
        
    #     elif context == "evening":
    #         # Prefer thriller/drama for evening viewing
    #         evening_genres = ['Thriller', 'Drama', 'Mystery']
    #         evening_boost = []
    #         others = []
            
    #         for movie in base_recs:
    #             movie_genres = [g.name for g in movie.genres.all()]
    #             if any(genre in evening_genres for genre in movie_genres):
    #                 evening_boost.append(movie)
    #             else:
    #                 others.append(movie)
            
    #         return evening_boost + others
        
    #     return base_recs
    def get_contextual_recommendations(self, context="general", limit=20):
        """Get recommendations based on context (time of day, season, etc.)"""
        base_recs = self.get_recommendations(limit)
        
        if context == "weekend":
            # Prefer longer, more engaging movies for weekends
            weekend_boost = Movie.objects.filter(
                runtime__gte=120,  # 2+ hours
                id__in=[m.id for m in base_recs]
            )
            # Apply disliked genre filter
            if self.user and self.user.is_authenticated:
                weekend_boost = self.filter_disliked_genres(weekend_boost)
            
            return list(weekend_boost) + [m for m in base_recs if m not in weekend_boost]
        
        elif context == "evening":
            # Prefer thriller/drama for evening viewing
            evening_genres = ['Thriller', 'Drama', 'Mystery']
            evening_boost = []
            others = []
            
            for movie in base_recs:
                movie_genres = [g.name for g in movie.genres.all()]
                if any(genre in evening_genres for genre in movie_genres):
                    evening_boost.append(movie)
                else:
                    others.append(movie)
            
            return evening_boost + others
        
        return base_recs
    def explain_recommendation(self, movie):
        """Provide explanation for why a movie was recommended"""
        if not self.user or not self.user.is_authenticated:
            return "Popular movie based on overall ratings"
        
        explanations = []
        
        # Check genre match
        user_ratings = UserRating.objects.filter(
            user=self.user, rating__gte=8.0
        ).select_related('movie').prefetch_related('movie__genres')
        
        if user_ratings.exists():
            user_genres = set()
            for rating in user_ratings:
                user_genres.update(g.name for g in rating.movie.genres.all())
            
            movie_genres = set(g.name for g in movie.genres.all())
            common_genres = user_genres & movie_genres
            
            if common_genres:
                explanations.append(f"You enjoyed {', '.join(common_genres)} movies")
        
        # Check director match
        if movie.director:
            director_movies = UserRating.objects.filter(
                user=self.user,
                movie__director=movie.director,
                rating__gte=7.0
            ).count()
            
            if director_movies > 0:
                explanations.append(f"You liked other movies by {movie.director}")
        
        # Check rating quality
        if movie.average_rating and movie.average_rating >= 8.0:
            explanations.append(f"Highly rated ({movie.average_rating:.1f}/10)")
        
        # Check popularity
        if movie.rating_count and movie.rating_count > 1000:
            explanations.append("Popular among users")
        
        return " • ".join(explanations) if explanations else "Recommended based on your preferences"
    
    def filter_disliked_genres(self, queryset):
        """Filter out movies with disliked genres (case-insensitive)"""
        if not self.preferences or not self.preferences.disliked_genres.exists():
            return queryset
        
        disliked_genre_names = [
            g.name.lower() for g in self.preferences.disliked_genres.all()
        ]
        
        print(f"Filtering out disliked genres: {disliked_genre_names}")  # Debug
        
        # Use case-insensitive filtering
        for genre_name in disliked_genre_names:
            queryset = queryset.exclude(genres__name__iexact=genre_name)
        
        return queryset.distinct()