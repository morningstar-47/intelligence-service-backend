from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche Python
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.base import Base
from app.models.user import User

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpreter la section .ini file en fonction de sa position
fileConfig(config.config_file_name)

# Ajouter l'URL de la base de données de l'application
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()