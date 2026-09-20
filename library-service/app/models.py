from sqlalchemy import Column, Integer, String, Boolean, DateTime
from .database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    category = Column(String, nullable=False)
    available = Column(Boolean, default=True)


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)

    book_id = Column(Integer, nullable=False)

    borrower_name = Column(String, nullable=False)
    borrower_email = Column(String, nullable=False)

    borrow_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)

    status = Column(
        String,
        nullable=False,
        default="BORROWED"
    )