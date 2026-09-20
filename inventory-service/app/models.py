from sqlalchemy import Column, Integer
from .database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, unique=True, nullable=False, index=True)
    total_copies = Column(Integer, nullable=False)
    available_copies = Column(Integer, nullable=False)