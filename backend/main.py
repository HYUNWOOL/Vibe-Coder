from fastapi import FastAPI
from sqlalchemy import text
from db import engine

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/db-ping")
def db_ping():
    with engine.connect() as conn:
        v = conn.execute(text("SELECT 1")).scalar_one()
    return {"db": v}
