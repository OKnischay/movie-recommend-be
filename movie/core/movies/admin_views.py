from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .tmdb_utils import search_and_import_movie, sync_movie_by_tmdb_id, bulk_import_popular_movies

class ImportMovieView(APIView):
    def post(self, request):
        mode = request.data.get("mode")
        query = request.data.get("query")

        try:
            if mode == "search":
                movie, msg = search_and_import_movie(query)
                return Response({"message": msg}, status=200 if movie else 400)

            elif mode == "tmdb":
                movie = sync_movie_by_tmdb_id(query)
                return Response({"message": f"Imported {movie.title}" if movie else "Not found"}, status=200 if movie else 404)

            elif mode == "popular":
                result = bulk_import_popular_movies(pages=3, skip_existing=True)
                return Response(result, status=200)

            return Response({"error": "Invalid mode"}, status=400)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
