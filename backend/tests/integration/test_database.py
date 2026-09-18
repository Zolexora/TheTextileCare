from sqlalchemy import text

from app.dependencies import engine


def test_database_engine_is_available() -> None:
    with engine.connect() as connection:
        result = connection.execute(text('SELECT 1'))
        assert result.scalar_one() == 1
