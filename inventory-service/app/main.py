from fastapi import FastAPI, Request

from .database import Base, engine
from .routers.inventory import router as inventory_router
from .routers import auth

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# Create database tables
Base.metadata.create_all(bind=engine)


# Create rate limiter
limiter = Limiter(
    key_func=get_remote_address
)


# Create FastAPI application
app = FastAPI(
    title="Inventory Microservice",
    description="Book Inventory Microservice for Library Management",
    version="1.0.0"
)


# Attach limiter
app.state.limiter = limiter


# Register rate limit handler
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# Include routers
app.include_router(inventory_router)
app.include_router(auth.router)


@app.get("/")
@limiter.limit("5/minute")
def root(request: Request):
    return {
        "message": "Inventory Microservice is running"
    }