from fastapi import FastAPI, Request, Depends, Header, HTTPException
from sqlalchemy.orm import Session
import httpx
import os

from .database import Base, engine, get_db
from .models import Book, Loan
from .routers.books import router as books_router
from .routers.borrow import router as borrow_router
from .routers import auth
from .security import get_current_user

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# =====================================
# CREATE DATABASE TABLES
# =====================================

Base.metadata.create_all(bind=engine)


# =====================================
# CREATE RATE LIMITER
# =====================================

limiter = Limiter(
    key_func=get_remote_address
)


# =====================================
# CREATE FASTAPI APPLICATION
# =====================================

app = FastAPI(
    title="Library Microservice",
    description="Library Management Microservice using FastAPI, SQLite, JWT and Rate Limiting",
    version="1.0.0"
)


# =====================================
# ATTACH RATE LIMITER
# =====================================

app.state.limiter = limiter


# =====================================
# RATE LIMIT EXCEPTION HANDLER
# =====================================

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# =====================================
# INCLUDE ROUTERS
# =====================================

app.include_router(books_router)
app.include_router(borrow_router)
app.include_router(auth.router)


# =====================================
# ROOT ENDPOINT
# =====================================

@app.get("/")
@limiter.limit("5/minute")
def root(request: Request):
    return {
        "message": "Library Microservice is running"
    }


# =====================================
# LIBRARY STATISTICS
# =====================================

@app.get("/statistics")
@limiter.limit("10/minute")
def get_statistics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    authorization: str = Header(None)
):

    # Total books
    total_books = db.query(Book).count()

    # Active loans
    active_loans = (
        db.query(Loan)
        .filter(Loan.status == "BORROWED")
        .count()
    )

    # Returned books
    returned_books = (
        db.query(Loan)
        .filter(Loan.status == "RETURNED")
        .count()
    )

    # Get inventory information
    try:

        response = httpx.get(
            f"{os.getenv('INVENTORY_SERVICE_URL', 'http://127.0.0.1:8002')}/inventory/",
            headers={
                "Authorization": authorization
            },
            timeout=5.0
        )

    except httpx.RequestError:

        raise HTTPException(
            status_code=503,
            detail="Inventory Service is unavailable"
        )

    # Check Inventory response
    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail="Unable to retrieve inventory statistics"
        )

    inventory_data = response.json()

    # Calculate available copies
    available_copies = sum(
        item["available_copies"]
        for item in inventory_data
    )

    return {
        "total_books": total_books,
        "active_loans": active_loans,
        "returned_books": returned_books,
        "available_copies": available_copies
    }