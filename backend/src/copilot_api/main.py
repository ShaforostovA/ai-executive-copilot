"""Minimal application used to validate the repository bootstrap."""

from fastapi import FastAPI

app = FastAPI(title="AI Executive Co-pilot API", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
