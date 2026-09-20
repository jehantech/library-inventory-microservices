from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database import get_db
from ..models import Book
from ..schemas import BookCreate, BookResponse
from ..security import get_current_user


router = APIRouter(
    prefix="/books",
    tags=["Books"]
)


limiter = Limiter(
    key_func=get_remote_address
)


@router.post("/", response_model=BookResponse)
@limiter.limit("5/minute")
def create_book(
    request: Request,
    book: BookCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    new_book = Book(
        title=book.title,
        author=book.author,
        category=book.category,
        available=True
    )

    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    return new_book


@router.get("/", response_model=list[BookResponse])
@limiter.limit("10/minute")
def get_books(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    return db.query(Book).all()


@router.get("/{book_id}", response_model=BookResponse)
@limiter.limit("10/minute")
def get_book(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    book = (
        db.query(Book)
        .filter(Book.id == book_id)
        .first()
    )

    if not book:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    return book


@router.put("/{book_id}", response_model=BookResponse)
@limiter.limit("5/minute")
def update_book(
    request: Request,
    book_id: int,
    book_data: BookCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    book = (
        db.query(Book)
        .filter(Book.id == book_id)
        .first()
    )

    if not book:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    book.title = book_data.title
    book.author = book_data.author
    book.category = book_data.category

    db.commit()
    db.refresh(book)

    return book


@router.delete("/{book_id}")
@limiter.limit("5/minute")
def delete_book(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    book = (
        db.query(Book)
        .filter(Book.id == book_id)
        .first()
    )

    if not book:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    db.delete(book)
    db.commit()

    return {
        "message": "Book deleted successfully"
    }