from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine


def main() -> None:
    settings = get_settings()
    with engine.connect() as connection:
        result = connection.execute(text("select 1")).scalar_one()
    print(f"Database connection OK for {settings.environment}: {result}")


if __name__ == "__main__":
    main()
