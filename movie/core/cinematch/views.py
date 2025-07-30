from django.utils.timezone import now, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Avg
from movies.models import Movie, UserRating as Rating
from users.models import CustomUser as User


@api_view(["GET"])
def dashboard_metrics(request):
    today = now().date()
    one_week_ago = now() - timedelta(days=7)
    one_month_ago = now() - timedelta(days=30)
    MIN_RATINGS_FOR_TOP_MOVIE = 1
    MIN_RATINGS_FOR_UNDERRATED = 3

    normal_users_qs = User.objects.filter(is_staff=False, is_superuser=False)

    total_users = normal_users_qs.count()
    new_users_week = normal_users_qs.filter(date_joined__gte=one_week_ago).count()
    new_users_month = normal_users_qs.filter(date_joined__gte=one_month_ago).count()
    active_users_week = normal_users_qs.filter(last_login__gte=one_week_ago).count()

    user_growth_rate = (
        round((new_users_week / (total_users - new_users_week)) * 100, 2)
        if total_users > new_users_week
        else 100
    )

    # Movie Metrics
    total_movies = Movie.objects.count()
    new_movies_week = Movie.objects.filter(created_at__gte=one_week_ago).count()
    underrated_movies_count = (
        Movie.objects.annotate(ratings_count=Count("user_ratings"))
        .filter(ratings_count__lt=MIN_RATINGS_FOR_UNDERRATED)
        .count()
    )

    # Rating Metrics
    avg_rating = Rating.objects.aggregate(avg=Avg("rating"))["avg"] or 0
    total_ratings = Rating.objects.count()
    ratings_this_week = Rating.objects.filter(created_at__gte=one_week_ago).count()
    avg_ratings_per_user = round(total_ratings / total_users, 2) if total_users else 0

    # Top Movies
    top_rated_movie = (
        Movie.objects
        .annotate(avg_rating=Avg('user_ratings__rating'), ratings_count=Count('user_ratings'))
        .filter(ratings_count__gte=MIN_RATINGS_FOR_TOP_MOVIE)
        .order_by('-avg_rating', '-ratings_count')  # break ties by rating count
        .first()
)



    if not top_rated_movie:
        print("No movie meets the minimum rating count threshold.")

    most_rated_movie = (
        Movie.objects.annotate(ratings_count=Count("user_ratings"))
        .order_by("-ratings_count")
        .first()
    )

    return Response(
        {
            # Users
            "total_users": total_users,
            "new_users_this_week": new_users_week,
            "new_users_this_month": new_users_month,
            "active_users_this_week": active_users_week,
            "user_growth_rate_percent": user_growth_rate,
            # Movies
            "total_movies": total_movies,
            "new_movies_this_week": new_movies_week,
            "underrated_movies_count": underrated_movies_count,
            # Ratings
            "total_ratings": total_ratings,
            "average_rating": round(avg_rating, 2),
            "ratings_this_week": ratings_this_week,
            "avg_ratings_per_user": avg_ratings_per_user,
            # Top Movies
            "top_rated_movie_title": (
                top_rated_movie.title if top_rated_movie else "N/A"
            ),
            "top_rated_movie_score": (
                round(top_rated_movie.avg_rating, 2) if top_rated_movie else 0
            ),
            "most_rated_movie_title": (
                most_rated_movie.title if most_rated_movie else "N/A"
            ),
            "most_rated_movie_count": (
                most_rated_movie.ratings_count if most_rated_movie else 0
            ),
        }
    )
