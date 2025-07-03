# movies/serializers.py
from rest_framework import serializers
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
            'average_rating', 'rating_count', 'user_rating', 'is_in_watchlist'
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
    movie_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserRating
        fields = ['id', 'movie', 'movie_id', 'rating', 'review', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

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
