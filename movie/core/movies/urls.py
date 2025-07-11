# movies/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Movie CRUD operations
    path('movies/', views.MovieListView.as_view(), name='movie-list'),
    path('movies/<int:pk>/', views.MovieDetailView.as_view(), name='movie-detail'),
    path('genres/', views.GenreListView.as_view(), name='genre-list'),
    
    # TMDB Integration
    path('import/tmdb/', views.import_tmdb_movie_view, name='import-tmdb-movie'),
    path('search/tmdb/', views.search_tmdb_movies_view, name='search-tmdb-movies'),
    path('search/import/', views.search_and_import_view, name='search-and-import'),
    path('popular/tmdb/', views.popular_movies_view, name='popular-tmdb-movies'),
    path('movies/tmdb/<int:tmdb_id>/', views.movie_by_tmdb_id_view, name='movie-by-tmdb-id'),
    
    # Recommendations
    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('trending/', views.trending_movies_view, name='trending-movies'),
    path('similar/<int:movie_id>/', views.similar_movies_view, name='similar-movies'),
    
    # User ratings
    path('ratings/', views.UserRatingListCreateView.as_view(), name='user-ratings'),
    path('ratings/<int:pk>/', views.UserRatingDetailView.as_view(), name='user-rating-detail'),
    
    # User preferences
    path('preferences/', views.UserPreferenceView.as_view(), name='user-preferences'),
    
    # Watchlist — changed movie_id to tmdb_id here
    path('watchlist/<int:tmdb_id>/', views.watchlist_view, name='watchlist'),
    path('watchlist/status/', views.watchlist_status_view, name='watchlist-status'),
    path('watchlist/user/<uuid:user_id>',views.UserWatchlistAPIView.as_view(),name='user_watchlist'),
    # Favorites — changed movie_id to tmdb_id here
    path('favorites/', views.user_favorites_view, name='user-favorites'),
    path('favorites/<int:tmdb_id>/', views.favorite_view, name='favorite'),
    path("favorites/movies/<uuid:user_id>/", views.user_favorite_movies_view, name="user-favorite-movies"),
    path('favorites/status/', views.favorite_status_view, name='favorite-status'),
    
    # Statistics
    path('stats/', views.movie_stats_view, name='movie-stats'),
]
