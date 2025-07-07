# movies/serializers.py
from rest_framework import serializers

from movies.tmdb_utils import sync_movie_by_tmdb_id
from .models import Favorite, Movie, Genre, UserRating, UserPreference, Watchlist, WatchHistory

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']

class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    user_rating = serializers.SerializerMethodField()
    is_in_watchlist = serializers.SerializerMethodField()
    
    class Meta:
        model = Movie
        fields = [
            'id', 'title', 'description', 'release_date', 'duration',
            'poster_url', 'trailer_url', 'director', 'cast', 'genres',
            'average_rating', 'rating_count', 'user_rating', 'is_in_watchlist',
            'poster_path', 'backdrop_path', 'imdb_id', 'tmdb_id'
        ]
    
    def get_user_rating(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            rating = UserRating.objects.filter(user=user, movie=obj).first()
            return rating.rating if rating else None
        return None
    
    def get_is_in_watchlist(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Watchlist.objects.filter(user=user, movie=obj).exists()
        return False


class UserRatingSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    tmdb_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserRating
        fields = ['id', 'movie', 'tmdb_id', 'rating', 'created_at', 'updated_at']

    def validate_rating(self, value):
        if value < 0 or value > 10:
            raise serializers.ValidationError("Rating must be between 0 and 10.")
        return value

    def validate_tmdb_id(self, value):
        if not value:
            raise serializers.ValidationError("TMDB ID is required.")
        return value

    # def create(self, validated_data):
    #     print(f"Creating rating with validated_data: {validated_data}")
    #     request = self.context['request']
    #     user = request.user
    #     tmdb_id = validated_data.pop('tmdb_id')
        
    #     # Check if movie exists or import it
    #     movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    #     if not movie:
    #         try:
    #             movie = sync_movie_by_tmdb_id(tmdb_id)
    #             if not movie:
    #                 raise serializers.ValidationError("Could not fetch movie from TMDB.")
    #         except Exception as e:
    #             print(f"Error syncing movie: {e}")
    #             raise serializers.ValidationError(f"Error fetching movie: {str(e)}")

    #     # Check if user already rated this movie
    #     existing_rating = UserRating.objects.filter(user=user, movie=movie).first()
    #     if existing_rating:
    #         raise serializers.ValidationError("You have already rated this movie.")

    #     try:
    #         return UserRating.objects.create(
    #             user=user,
    #             movie=movie,
    #             rating=validated_data['rating']
    #         )
    #     except Exception as e:
    #         print(f"Error creating rating: {e}")
    #         raise serializers.ValidationError(f"Error creating rating: {str(e)}")
    def create(self, validated_data):
        print(f"Creating rating with validated_data: {validated_data}")
        request = self.context['request']
        user = request.user
        tmdb_id = validated_data.pop('tmdb_id')
        
        # Check if movie exists or import it
        movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
        if not movie:
            try:
                movie = sync_movie_by_tmdb_id(tmdb_id)
                if not movie:
                    raise serializers.ValidationError("Could not fetch movie from TMDB.")
            except Exception as e:
                print(f"Error syncing movie: {e}")
                raise serializers.ValidationError(f"Error fetching movie: {str(e)}")

        # This will either update existing rating or create new one
        rating, created = UserRating.objects.update_or_create(
            user=user,
            movie=movie,
            defaults={'rating': validated_data['rating']}
        )
        
        action = "Created" if created else "Updated"
        print(f"{action} rating: {rating.rating}")
        
        return rating
class UserPreferenceSerializer(serializers.ModelSerializer):
    favorite_genres = GenreSerializer(many=True, read_only=True)
    favorite_genre_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    disliked_genres = GenreSerializer(many=True, read_only=True)
    disliked_genre_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    
    class Meta:
        model = UserPreference
        fields = [
            'favorite_genres', 'favorite_genre_ids', 'disliked_genres', 'disliked_genre_ids',
            'genre_weight', 'rating_weight', 'popularity_weight', 'recency_weight'
        ]
    
    def update(self, instance, validated_data):
        favorite_genre_ids = validated_data.pop('favorite_genre_ids', None)
        disliked_genre_ids = validated_data.pop('disliked_genre_ids', None)
        
        instance = super().update(instance, validated_data)
        
        if favorite_genre_ids is not None:
            instance.favorite_genres.set(favorite_genre_ids)
        
        if disliked_genre_ids is not None:
            instance.disliked_genres.set(disliked_genre_ids)
        
        return instance
    
class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'movie', 'created_at']
        read_only_fields = ['user', 'created_at']

class FavoriteMovieDetailSerializer(serializers.ModelSerializer):
    movie = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ["id", "created_at", "movie"]

    def get_movie(self, obj):
        return MovieSerializer(obj.movie, context=self.context).data
class WatchlistSerializer(serializers.ModelSerializer):
    movie = MovieSerializer()

    class Meta:
        model = Watchlist
        fields = ['id','movie', 'user']
