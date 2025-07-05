from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from movies.tmdb_utils import (
    bulk_import_popular_movies, 
    search_and_import_movie, 
    sync_movie_by_tmdb_id,
    get_trending_movies
)
from movies.models import Movie
import time

class Command(BaseCommand):
    help = 'Import movies from TMDB API with various import strategies'
    
    # Constants
    RATE_LIMIT_DELAY = 0.25  # seconds between API calls
    DEFAULT_POPULAR_PAGES = 1
    DEFAULT_BATCH_SIZE = 10

    def add_arguments(self, parser):
        # Mutually exclusive flags
        import_group = parser.add_mutually_exclusive_group(required=True)

        import_group.add_argument(
            '--popular',
            type=int,
            nargs='?',
            const=self.DEFAULT_POPULAR_PAGES,
            help=f'Import popular movies (default: {self.DEFAULT_POPULAR_PAGES} page)'
        )
        
        import_group.add_argument(
            '--trending',
            action='store_true',
            help='Import trending movies (last 7 days)'
        )
        
        import_group.add_argument(
            '--search',
            type=str,
            help='Search and import a specific movie by title'
        )
        
        import_group.add_argument(
            '--tmdb-id',
            type=int,
            help='Import a specific movie by TMDB ID'
        )

        # Optional modifiers
        parser.add_argument(
            '--batch-size',
            type=int,
            default=self.DEFAULT_BATCH_SIZE,
            help=f'Batch size for imports (default: {self.DEFAULT_BATCH_SIZE})'
        )
        
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip movies that already exist in the database'
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable detailed output'
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.skip_existing = options['skip_existing']
        batch_size = options['batch_size']

        try:
            if options['popular'] is not None:
                pages = options['popular'] or self.DEFAULT_POPULAR_PAGES
                self.stdout.write(f"Importing {pages} page(s) of popular movies...")
                self.import_popular_movies(pages, batch_size)

            elif options['trending']:
                self.stdout.write("Importing trending movies...")
                self.import_trending_movies()

            elif options['search']:
                query = options['search']
                self.stdout.write(f"Searching and importing: '{query}'")
                self.search_and_import(query)

            elif options['tmdb_id']:
                tmdb_id = options['tmdb_id']
                self.stdout.write(f"Importing movie with TMDB ID: {tmdb_id}")
                self.import_by_tmdb_id(tmdb_id)

        except Exception as e:
            raise CommandError(f"Import failed: {str(e)}")

    def import_popular_movies(self, pages, batch_size):
        """Import popular movies from TMDB"""
        try:
            result = bulk_import_popular_movies(
                pages=pages,
                skip_existing=self.skip_existing,
                batch_size=batch_size
            )
            self.print_import_stats(result)

        except Exception as e:
            raise CommandError(f"Error importing popular movies: {str(e)}")

    def import_trending_movies(self):
        """Import trending movies from TMDB"""
        try:
            trending_data = get_trending_movies()
            if not trending_data or 'results' not in trending_data:
                raise CommandError("No trending movies data received from TMDB")

            movies = trending_data["results"]
            stats = {'imported': 0, 'skipped': 0, 'failed': 0}

            for movie_data in movies:
                self.process_movie_data(movie_data, stats)
                time.sleep(self.RATE_LIMIT_DELAY)

            self.print_import_stats(stats)

        except Exception as e:
            raise CommandError(f"Error importing trending movies: {str(e)}")

    def search_and_import(self, query):
        """Search and import a specific movie by title"""
        try:
            result = search_and_import_movie(
                query,
                skip_existing=self.skip_existing
            )

            if result.get('movie'):
                status = "Found existing" if result.get('existing') else "Imported new"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{status} movie: {result['movie'].title} (TMDB ID: {result['movie'].tmdb_id})"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(result.get('message', 'Unknown error')))

        except Exception as e:
            raise CommandError(f"Search failed: {str(e)}")

    def import_by_tmdb_id(self, tmdb_id):
        """Import a specific movie by TMDB ID"""
        try:
            if self.skip_existing and Movie.objects.filter(tmdb_id=tmdb_id).exists():
                movie = Movie.objects.get(tmdb_id=tmdb_id)
                self.stdout.write(self.style.WARNING(f"Movie already exists: {movie.title}"))
                return

            movie = sync_movie_by_tmdb_id(tmdb_id)
            if movie:
                self.stdout.write(self.style.SUCCESS(f"Successfully imported: {movie.title}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to import TMDB ID: {tmdb_id}"))

        except Exception as e:
            raise CommandError(f"Error importing movie: {str(e)}")

    def process_movie_data(self, movie_data, stats):
        """Helper to process single movie"""
        tmdb_id = movie_data.get('id')
        title = movie_data.get('title', 'Unknown')

        if not tmdb_id:
            stats['failed'] += 1
            if self.verbose:
                self.stdout.write(self.style.ERROR("Invalid movie data (missing ID)"))
            return

        try:
            if self.skip_existing and Movie.objects.filter(tmdb_id=tmdb_id).exists():
                stats['skipped'] += 1
                if self.verbose:
                    self.stdout.write(f"Skipped existing: {title}")
                return

            with transaction.atomic():
                movie = sync_movie_by_tmdb_id(tmdb_id)
                if movie:
                    stats['imported'] += 1
                    if self.verbose:
                        self.stdout.write(self.style.SUCCESS(f"Imported: {title}"))
                else:
                    stats['failed'] += 1
                    if self.verbose:
                        self.stdout.write(self.style.ERROR(f"Failed: {title}"))

        except Exception as e:
            stats['failed'] += 1
            if self.verbose:
                self.stdout.write(self.style.ERROR(f"Error processing {title}: {str(e)}"))

    def print_import_stats(self, stats):
        """Print a summary of the import operation"""
        self.stdout.write("\n=== Import Summary ===")
        self.stdout.write(f"Imported: {self.style.SUCCESS(str(stats.get('imported', 0)))}")
        self.stdout.write(f"Skipped: {self.style.WARNING(str(stats.get('skipped', 0)))}")
        self.stdout.write(f"Failed:  {self.style.ERROR(str(stats.get('failed', 0)))}")
