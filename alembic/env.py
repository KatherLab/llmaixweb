from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from backend.src.db.base import Base

# Import models for metadata - must happen after Base import
# but we avoid importing config at module level to prevent .env checks
# Models are imported here but they don't depend on config
from backend.src.models import *  # noqa: F403

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# PostgreSQL-only trigram indexes (add_perf_indexes_2026_06_16) are created by
# migration but intentionally NOT declared on the models — SQLite databases
# bootstrapped via create_all() can't build GIN/pg_trgm indexes. Hide them from
# autogenerate / `alembic check` so they aren't proposed for removal.
_MIGRATION_ONLY_INDEXES = {"ix_documents_text_trgm", "ix_files_file_name_trgm"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "index" and name in _MIGRATION_ONLY_INDEXES:
        return False
    return True


def get_url():
    """Get the database URL from settings."""
    # Import settings lazily to avoid .env checks during module import
    from backend.src.core.config import settings

    url = settings.SQLALCHEMY_DATABASE_URI
    if url is None:
        # Construct from individual components
        url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = get_url()

    # Build the engine directly from the URL. Routing it through
    # config.set_main_option() would hand it to ConfigParser, which treats a
    # "%" in the DB password as an interpolation marker and crashes.
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        # Serialize concurrent `alembic upgrade head` runs (e.g. several
        # backend replicas booting at once) with a session-level advisory
        # lock; it is released automatically when this connection closes.
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "SELECT pg_advisory_lock(hashtext('llmaixweb_alembic_migrations'))"
            )
            # End the transaction the lock statement auto-began — otherwise
            # alembic sees an "external" transaction and never commits the
            # migrations. The session-level advisory lock survives the commit
            # and is held until this connection closes.
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
