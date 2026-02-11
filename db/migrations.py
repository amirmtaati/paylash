from sqlalchemy import inspect, text


def ensure_users_custom_id_column(engine):
    """Add users.custom_id for existing SQLite databases."""
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}

    with engine.begin() as conn:
        if "custom_id" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN custom_id VARCHAR(64)"))

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_custom_id "
                "ON users(custom_id) WHERE custom_id IS NOT NULL"
            )
        )
