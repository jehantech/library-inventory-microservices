from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class BookCreate(BaseModel):
    title: str
    author: str
    category: str


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    category: str
    available: bool

    model_config = ConfigDict(from_attributes=True)


class BorrowRequest(BaseModel):
    borrower_name: str
    borrower_email: EmailStr
    book_id: int


class LoanResponse(BaseModel):
    id: int
    book_id: int
    borrower_name: str
    borrower_email: str
    borrow_date: datetime
    due_date: datetime
    return_date: datetime | None
    status: str

    model_config = ConfigDict(from_attributes=True)