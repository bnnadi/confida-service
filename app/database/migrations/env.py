from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from alembic import context

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import our models and configuration
from app.database.connection import Base
from app.config import get_settings
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from settings with enhanced error handling
try:
    settings = get_settings()
    database_url = settings.DATABASE_URL
    config.set_main_option("sqlalchemy.url", database_url)
    logger.info(f"Database URL configured for migrations: {database_url.split('@')[0]}@***")
except Exception as e:
    logger.error(f"Failed to get database settings: {e}")
    # Fallback to environment variable or default
    database_url = os.getenv("DATABASE_URL", "postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev")
    config.set_main_option("sqlalchemy.url", database_url)
    logger.warning(f"Using fallback database URL: {database_url.split('@')[0]}@***")

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    logger.info(f"Running migrations in offline mode for: {url.split('@')[0]}@***")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logger.info("Running migrations in online mode")
    
    # Get configuration with enhanced error handling
    configuration = config.get_section(config.config_ini_section, {})
    
    # Add connection pool settings for better performance
    configuration.setdefault("sqlalchemy.pool_size", "5")
    configuration.setdefault("sqlalchemy.max_overflow", "10")
    configuration.setdefault("sqlalchemy.pool_timeout", "30")
    configuration.setdefault("sqlalchemy.pool_recycle", "3600")
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
