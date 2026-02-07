from fastapi import FastAPI

from app.core.logging import init_logging
from app.routers.debug_flights import router as debug_flights_router
from app.routers.debug_hotels import router as debug_hotels_router
from app.routers.itinerary import router as itinerary_router
from app.routers.search import router as search_router

init_logging()

app = FastAPI(title="Vibecoder Travel Recommender")
app.include_router(debug_flights_router, prefix="/api/debug", tags=["debug"])
app.include_router(debug_hotels_router, prefix="/api/debug", tags=["debug"])
app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(itinerary_router, prefix="/api", tags=["itinerary"])


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
