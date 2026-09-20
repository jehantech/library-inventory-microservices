from datetime import datetime, timedelta, timezone

import httpx

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Header
)

from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database import get_db
from ..models import Book, Loan
from ..schemas import BorrowRequest, LoanResponse
from ..security import get_current_user


router = APIRouter(
    prefix="/borrow",
    tags=["Library Transactions"]
)


limiter = Limiter(
    key_func=get_remote_address
)


import os

INVENTORY_SERVICE_URL = os.getenv(
    "INVENTORY_SERVICE_URL",
    "http://127.0.0.1:8002"
)


# =====================================
# BORROW BOOK
# =====================================

@router.post("/")
@limiter.limit("5/minute")
def borrow_book(
    request: Request,
    borrow_data: BorrowRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    authorization: str = Header(None)
):

    # Check whether book exists
    book = (
        db.query(Book)
        .filter(Book.id == borrow_data.book_id)
        .first()
    )

    if not book:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    # Contact Inventory Microservice
    try:

        response = httpx.post(
            f"{INVENTORY_SERVICE_URL}/inventory/{borrow_data.book_id}/borrow",
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

        try:
            detail = response.json().get(
                "detail",
                "Unable to allocate book copy"
            )

        except Exception:
            detail = "Unable to allocate book copy"

        raise HTTPException(
            status_code=response.status_code,
            detail=detail
        )

    inventory_result = response.json()

    # Keep Library book availability synchronized with Inventory Service
    book.available = inventory_result["available_copies"] > 0

    borrow_date = datetime.now(timezone.utc)

    due_date = borrow_date + timedelta(
        days=14
    )

    # Create loan record
    new_loan = Loan(
        book_id=borrow_data.book_id,
        borrower_name=borrow_data.borrower_name,
        borrower_email=borrow_data.borrower_email,
        borrow_date=borrow_date,
        due_date=due_date,
        return_date=None,
        status="BORROWED"
    )

    db.add(new_loan)
    db.commit()
    db.refresh(new_loan)

    return {
        "message": "Book borrowed successfully",

        "loan": {
            "loan_id": new_loan.id,
            "book_id": new_loan.book_id,
            "borrower_name": new_loan.borrower_name,
            "borrower_email": new_loan.borrower_email,
            "borrow_date": new_loan.borrow_date,
            "due_date": new_loan.due_date,
            "status": new_loan.status
        },

        "book": {
            "id": book.id,
            "title": book.title,
            "author": book.author
        },

        "inventory": inventory_result
    }


# =====================================
# RETURN BOOK
# =====================================

@router.post("/return/{loan_id}")
@limiter.limit("5/minute")
def return_book(
    request: Request,
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    authorization: str = Header(None)
):

    # Find loan
    loan = (
        db.query(Loan)
        .filter(Loan.id == loan_id)
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan record not found"
        )

    # Check whether already returned
    if loan.status == "RETURNED":

        raise HTTPException(
            status_code=400,
            detail="Book is already returned"
        )

    # Find associated book
    book = (
        db.query(Book)
        .filter(Book.id == loan.book_id)
        .first()
    )

    if not book:

        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    # Contact Inventory Microservice
    try:

        response = httpx.post(
            f"{INVENTORY_SERVICE_URL}/inventory/{loan.book_id}/return",
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

        try:
            detail = response.json().get(
                "detail",
                "Unable to return book copy"
            )

        except Exception:
            detail = "Unable to return book copy"

        raise HTTPException(
            status_code=response.status_code,
            detail=detail
        )

    inventory_result = response.json()

    # Keep Library book availability synchronized with Inventory Service
    book.available = inventory_result["available_copies"] > 0

    loan.return_date = datetime.now(timezone.utc)
    loan.status = "RETURNED"

    db.commit()
    db.refresh(loan)

    return {
        "message": "Book returned successfully",

        "loan": {
            "loan_id": loan.id,
            "borrower_name": loan.borrower_name,
            "borrower_email": loan.borrower_email,
            "return_date": loan.return_date,
            "status": loan.status
        },

        "book": {
            "id": book.id,
            "title": book.title
        },

        "inventory": inventory_result
    }


# =====================================
# GET ALL LOANS
# =====================================

@router.get(
    "/loans",
    response_model=list[LoanResponse]
)
@limiter.limit("10/minute")
def get_loans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    return db.query(Loan).all()


# =====================================
# GET LOAN BY ID
# =====================================

@router.get(
    "/loans/{loan_id}",
    response_model=LoanResponse
)
@limiter.limit("10/minute")
def get_loan(
    request: Request,
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    loan = (
        db.query(Loan)
        .filter(Loan.id == loan_id)
        .first()
    )

    if not loan:

        raise HTTPException(
            status_code=404,
            detail="Loan record not found"
        )

    return loan

# =====================================
# CALCULATE FINE
# =====================================

@router.get("/loans/{loan_id}/fine")
@limiter.limit("10/minute")
def calculate_fine(
    request: Request,
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    # Fine per overdue day
    FINE_PER_DAY = 10

    # Find loan
    loan = (
        db.query(Loan)
        .filter(Loan.id == loan_id)
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail="Loan record not found"
        )

    # Determine end date
    if loan.status == "RETURNED":
        end_date = loan.return_date
    else:
        end_date = datetime.now(timezone.utc)

    # Calculate overdue days
    if end_date <= loan.due_date:

        overdue_days = 0
        fine_amount = 0

    else:

        overdue_seconds = (
            end_date - loan.due_date
        ).total_seconds()

        overdue_days = int(
            overdue_seconds // 86400
        )

        # Count a partial day as one overdue day
        if overdue_seconds % 86400 > 0:
            overdue_days += 1

        fine_amount = overdue_days * FINE_PER_DAY

    return {
        "loan_id": loan.id,
        "borrower_name": loan.borrower_name,
        "book_id": loan.book_id,
        "due_date": loan.due_date,
        "return_date": loan.return_date,
        "status": loan.status,
        "overdue_days": overdue_days,
        "fine_per_day": FINE_PER_DAY,
        "fine_amount": fine_amount,
        "currency": "INR"
    }