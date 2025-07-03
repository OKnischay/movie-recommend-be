# movies/urls.py
from django.urls import path
from . import views

urlpatterns = [
 
    path('movies/', views.MovieListView.as_view(), name='movie-list'),
    path('movies/<int:pk>/', views.MovieDetailView.as_view(), name='movie-detail'),
    path('movies/<int:movie_id>/similar/', views.similar_movies_view, name='similar-movies'),
    
   
    path('genres/', views.GenreListView.as_view(), name='genre-list'),
    

    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('trending/', views.trending_movies_view, name='trending-movies'),
    
   
    path('ratings/', views.UserRatingListCreateView.as_view(), name='user-ratings'),
    path('ratings/<int:pk>/', views.UserRatingDetailView.as_view(), name='user-rating-detail'),
    
  
    path('preferences/', views.UserPreferenceView.as_view(), name='user-preferences'),
    
    path('watchlist/<int:movie_id>/', views.watchlist_view, name='watchlist-toggle'),
    path('watchlist/status/', views.watchlist_status_view, name='watchlist-status'),
    
    path('favorites/<int:movie_id>/', views.favorite_view, name='favorite-toggle'),
    path('favorites/status/', views.favorite_status_view, name='favorite-status'),
]
