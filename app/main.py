"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api import auth, checkout

app = FastAPI(title="Checkout Service", version="1.0.0")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(checkout.router, tags=["checkout"])


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple readiness indicator for load balancers and probes."""
    return {"status": "ok"}
