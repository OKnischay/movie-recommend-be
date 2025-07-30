from movies.models import Movie,Genre, UserRating, UserPreference, Watchlist, WatchHistory, Favorite, UserReview
from django.contrib import admin
class MovieAdmin(admin.ModelAdmin):
    search_fields = ['title', 'description', 'director', 'cast']

admin.site.register(Movie, MovieAdmin)  
admin.site.register(Genre)
admin.site.register(UserRating)
admin.site.register(UserPreference)
admin.site.register(Watchlist)
admin.site.register(WatchHistory)
admin.site.register(Favorite) 
admin.site.register(UserReview)