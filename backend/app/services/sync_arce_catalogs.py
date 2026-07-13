import asyncio

from app.db.session import Base, SessionLocal, engine
from app.models import catalog, purchase  # noqa: F401
from app.services.catalog_service import sync_official_catalogs


async def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = await sync_official_catalogs(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
