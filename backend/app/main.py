from fastapi import FastAPI

from app.core.logging import init_logging

init_logging()

app = FastAPI(title="Vibecoder Travel Recommender")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
