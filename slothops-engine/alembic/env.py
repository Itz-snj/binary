"""
SlothOps — Alembic Migration Environment
Uses psycopg (sync) driver via DIRECT_DATABASE_URL for migrations.
Imports all SQLModel table models so autogenerate can detect schema changes.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Add slothops-engine root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all table models so their metadata is registered
import db.models  # noqa: F401 — side-effect import registers all tables

config = context.config

# Override sqlalchemy.url from environment (DIRECT_DATABASE_URL for sync migrations)
direct_url = os.environ.get(
    "DIRECT_DATABASE_URL",
    "postgresql+psycopg://slothops:slothops_dev@localhost:5432/slothops",
)
config.set_main_option("sqlalchemy.url", direct_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
