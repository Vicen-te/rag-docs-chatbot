"""Install the Postgres extensions that the KB schema and search relies on."""
from django.core.management.base import BaseCommand
from django.db import connection

EXTENSIONS = ("vector",)


class Command(BaseCommand):
    help = "Install the pgvector extension on the current database."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for name in EXTENSIONS:
                cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {name};")
                self.stdout.write(self.style.SUCCESS(f"extension '{name}' ready"))
