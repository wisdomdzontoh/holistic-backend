"""
Management command: Copy all data from production (Render PostgreSQL) to local SQLite.

READ-ONLY from production: This command only READS from the prod database.
It never writes, updates, or deletes anything on production. All writes go to local db.sqlite3.

Usage:
  1. Set PROD_DATABASE_URL to your Render PostgreSQL connection string.
  2. Ensure DATABASE_URL is NOT set (so default DB stays SQLite), or use --local-db path.
  3. Run: python manage.py migrate_prod_to_local

  Example:
    set PROD_DATABASE_URL=postgres://user:pass@host/dbname?sslmode=require
    python manage.py migrate_prod_to_local
"""
import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.db import connection, connections, transaction
from django.apps import apps


# Source label - only used for reading. Never write to this.
PROD_ALIAS = "prod"
# Destination - where we write the copied data.
LOCAL_ALIAS = "default"


def get_concrete_models_in_dependency_order():
    """
    Return all concrete models (excluding proxies) in an order safe for
    serialization: a model is after any model it references via FK/M2M.
    """
    from django.db.models import Model
    from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField

    all_models = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if model._meta.proxy or not model._meta.managed:
                continue
            all_models.append(model)

    # Build dependency graph: model -> set of models it depends on (must be serialized first)
    deps = {}
    for model in all_models:
        deps[model] = set()
        for field in model._meta.get_fields():
            if getattr(field, "remote_field", None) is None:
                continue
            rel_model = getattr(field.remote_field, "model", None)
            if rel_model is None or rel_model == model:
                continue
            deps[model].add(rel_model)
            # For M2M, the through model or the related model
            if isinstance(field, ManyToManyField):
                through = getattr(field.remote_field, "through", None)
                if through and getattr(through, "_meta", None) and through._meta.managed:
                    deps[model].add(through)

    # Only consider deps that are in all_models
    model_set = set(all_models)
    deps_filtered = {m: deps[m] & model_set for m in all_models}

    result = []
    seen = set()

    def visit(m):
        if m in seen:
            return
        seen.add(m)
        for d in deps_filtered.get(m, ()):
            visit(d)
        result.append(m)

    for m in all_models:
        visit(m)

    return result


def copy_table_from_prod_to_local(model, prod_alias=PROD_ALIAS, local_alias=LOCAL_ALIAS, verbosity=1):
    """
    Serialize all rows of `model` from the prod DB and deserialize into the default (local) DB.
    No writes are performed on prod.
    """
    # Read only from prod; write only to local.
    qs = model.objects.using(prod_alias).all()
    count = qs.count()
    if count == 0:
        if verbosity > 1:
            print(f"  {model._meta.label}: 0 rows (skip)")
        return 0

    # Use a chunked iterator to avoid loading everything into memory
    batch_size = 500
    total_copied = 0
    label = model._meta.label

    try:
        with transaction.atomic(using=local_alias):
            for start in range(0, count, batch_size):
                batch = list(qs[start : start + batch_size])
                data = serializers.serialize("python", batch, use_natural_foreign_keys=False)
                for item in data:
                    obj = serializers.deserialize("python", [item], ignorenonexistent=True)
                    for deserialized in obj:
                        # Save only to local; we never touch prod.
                        deserialized.save(using=local_alias)
                        total_copied += 1
    except Exception as e:
        # Re-raise with context
        raise type(e)(f"Copying {label}: {e}").with_traceback(sys.exc_info()[2])

    if verbosity > 0:
        print(f"  {label}: {total_copied} rows")
    return total_copied


class Command(BaseCommand):
    help = (
        "Copy all data from production (Render) PostgreSQL to local SQLite. "
        "Read-only on prod; prod data is never modified or wiped."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-flush",
            action="store_true",
            help="Do not flush local tables before copy (default: flush local first for a clean copy).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only connect to prod and list tables/row counts; do not copy or flush.",
        )
        parser.add_argument(
            "--prod-url",
            type=str,
            default=os.environ.get("PROD_DATABASE_URL", ""),
            help="Production DB URL (default: PROD_DATABASE_URL env var).",
        )

    def handle(self, *args, **options):
        prod_url = (options.get("prod_url") or "").strip()
        if not prod_url:
            raise CommandError(
                "Production URL not set. Set PROD_DATABASE_URL or pass --prod-url.\n"
                "Example: set PROD_DATABASE_URL=postgres://user:pass@host/db?sslmode=require"
            )

        # Add prod DB from URL; do not replace default so local stays SQLite.
        try:
            import dj_database_url
            prod_config = dj_database_url.parse(prod_url)
        except ImportError:
            raise CommandError("Install dj-database-url: pip install dj-database-url")
        except Exception as e:
            raise CommandError(f"Invalid PROD_DATABASE_URL: {e}")

        # Ensure we never write to prod: we only ever READ using .using('prod').
        from django.conf import settings
        # Django backends may expect these keys on the config dict (avoid KeyError)
        for key, default in (
            ("OPTIONS", {}),
            ("TIME_ZONE", getattr(settings, "TIME_ZONE", "UTC")),
            ("AUTOCOMMIT", True),
            ("CONN_MAX_AGE", 0),
            ("ATOMIC_REQUESTS", False),
        ):
            prod_config.setdefault(key, default)
        settings.DATABASES[PROD_ALIAS] = prod_config
        if "default" in settings.DATABASES:
            default_config = settings.DATABASES["default"]
            default_config.setdefault("OPTIONS", {})
            default_config.setdefault(
                "TIME_ZONE", getattr(settings, "TIME_ZONE", "UTC")
            )
            default_config.setdefault("AUTOCOMMIT", True)
            default_config.setdefault("CONN_MAX_AGE", 0)
            default_config.setdefault("ATOMIC_REQUESTS", False)
        if PROD_ALIAS in connections:
            connections[PROD_ALIAS].close()
        # Connection to prod is created on first use from settings.DATABASES['prod']

        # Safety: require default DB to be SQLite so we never flush or write to prod
        default_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
        if "sqlite3" not in default_engine:
            raise CommandError(
                "Default database must be SQLite to avoid writing to production.\n"
                "Unset DATABASE_URL (or remove it from .env), then run again so that "
                "data is copied into local db.sqlite3 only."
            )

        verbosity = options.get("verbosity", 1)
        dry_run = options.get("dry_run", False)
        no_flush = options.get("no_flush", False)

        if dry_run:
            self.stdout.write("Dry run: checking production connection and row counts only.\n")
            try:
                conn = connections[PROD_ALIAS]
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                        """
                    )
                    tables = [r[0] for r in cur.fetchall()]
                self.stdout.write(f"Production tables: {len(tables)}\n")
                for t in tables[:30]:
                    with conn.cursor() as c:
                        c.execute(f'SELECT COUNT(*) FROM "{t}"')
                        n = c.fetchone()[0]
                    self.stdout.write(f"  {t}: {n} rows")
                if len(tables) > 30:
                    self.stdout.write(f"  ... and {len(tables) - 30} more tables")
            except Exception as e:
                raise CommandError(f"Prod connection failed: {e}")
            return

        if not no_flush:
            self.stdout.write("Flushing local database (only local data is affected)...")
            try:
                with connection.cursor() as cur:
                    # Default is SQLite (enforced above); use SQLite-specific flush
                    cur.execute("PRAGMA foreign_keys = OFF")
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                    for (name,) in cur.fetchall():
                        cur.execute(f'DELETE FROM "{name}"')
                    cur.execute("PRAGMA foreign_keys = ON")
            except Exception as e:
                raise CommandError(f"Flush failed: {e}")
            self.stdout.write(self.style.SUCCESS("Local DB flushed.\n"))

        models_order = get_concrete_models_in_dependency_order()
        self.stdout.write(f"Copying {len(models_order)} models from prod to local (read-only on prod)...\n")

        # Disable SQLite FK enforcement during copy so insert order doesn't trigger FK errors
        with connection.cursor() as cur:
            cur.execute("PRAGMA foreign_keys = OFF")

        total = 0
        try:
            for model in models_order:
                try:
                    n = copy_table_from_prod_to_local(
                        model,
                        prod_alias=PROD_ALIAS,
                        local_alias=LOCAL_ALIAS,
                        verbosity=verbosity,
                    )
                    total += n
                except Exception as e:
                    label = getattr(model, "_meta", None) and getattr(model._meta, "label", None) or str(model)
                    raise CommandError(f"Error copying {label}: {e}\n{type(e).__name__}: {e}")
        finally:
            with connection.cursor() as cur:
                cur.execute("PRAGMA foreign_keys = ON")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Total rows copied to local: {total}"))
        self.stdout.write("Production was only read from; no prod data was changed or wiped.")
