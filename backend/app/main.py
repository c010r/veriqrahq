import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.catalogs import router as catalogs_router
from app.api.purchases import router as purchases_router
from app.core.config import get_settings
from app.db.session import Base, engine
from app.models import catalog, purchase  # noqa: F401
from app.services.arce_sync import scheduler_loop

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_sync_scheduler() -> None:
    asyncio.create_task(scheduler_loop())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(purchases_router, prefix="/api")
app.include_router(catalogs_router, prefix="/api")
