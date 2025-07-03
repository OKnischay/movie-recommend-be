# movies/models.py
from django.db import models
from users.models import CustomUser as User
from django.core.validators import MinValueValidator, MaxValueValidator


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    release_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in minutes")
    poster_url = models.URLField(blank=True, null=True)
    trailer_url = models.URLField(blank=True, null=True)
    imdb_id = models.CharField(max_length=20, blank=True, null=True)
    tmdb_id = models.IntegerField(blank=True, null=True)
    
    # Movie metadata
    director = models.CharField(max_length=200, blank=True)
    cast = models.JSONField(default=list, blank=True)  # List of actor names
    genres = models.ManyToManyField(Genre, related_name='movies')
    
    # Aggregated ratings
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.release_date.year})"
    
    def update_rating(self):
        """Update average rating and count"""
        ratings = self.user_ratings.all()
        if ratings.exists():
            self.average_rating = ratings.aggregate(
                avg=models.Avg('rating')
            )['avg']
            self.rating_count = ratings.count()
        else:
            self.average_rating = 0
            self.rating_count = 0
        self.save()

class UserRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='user_ratings')
    rating = models.DecimalField(
        max_digits=2, 
        decimal_places=1,
        validators=[MinValueValidator(0.5), MaxValueValidator(5.0)]
    )
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'movie')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.movie.update_rating()

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    favorite_genres = models.ManyToManyField(Genre, blank=True)
    disliked_genres = models.ManyToManyField(Genre, blank=True, related_name='disliked_by')
    
    # Preference weights for recommendation algorithm
    genre_weight = models.FloatField(default=0.3)
    rating_weight = models.FloatField(default=0.4)
    popularity_weight = models.FloatField(default=0.2)
    recency_weight = models.FloatField(default=0.1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'movie')

class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    watched_at = models.DateTimeField(auto_now_add=True)
    completion_percentage = models.FloatField(default=100.0)
    
    class Meta:
        unique_together = ('user', 'movie')

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')  # Ensure a user can't favorite same movie twice
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s favorite: {self.movie.title}"