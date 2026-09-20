from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database import get_db
from ..models import Inventory
from ..schemas import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse
)
from ..security import get_current_user


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


limiter = Limiter(
    key_func=get_remote_address
)


@router.post("/", response_model=InventoryResponse)
@limiter.limit("5/minute")
def create_inventory(
    request: Request,
    inventory: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    existing = (
        db.query(Inventory)
        .filter(Inventory.book_id == inventory.book_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Inventory already exists for this book"
        )

    if inventory.total_copies <= 0:
        raise HTTPException(
            status_code=400,
            detail="Total copies must be greater than zero"
        )

    new_inventory = Inventory(
        book_id=inventory.book_id,
        total_copies=inventory.total_copies,
        available_copies=inventory.total_copies
    )

    db.add(new_inventory)
    db.commit()
    db.refresh(new_inventory)

    return new_inventory


@router.get("/", response_model=list[InventoryResponse])
@limiter.limit("10/minute")
def get_inventory(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    return db.query(Inventory).all()


@router.get("/{book_id}", response_model=InventoryResponse)
@limiter.limit("10/minute")
def get_book_inventory(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    inventory = (
        db.query(Inventory)
        .filter(Inventory.book_id == book_id)
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found"
        )

    return inventory


@router.put("/{book_id}", response_model=InventoryResponse)
@limiter.limit("5/minute")
def update_inventory(
    request: Request,
    book_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    inventory = (
        db.query(Inventory)
        .filter(Inventory.book_id == book_id)
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found"
        )

    borrowed_copies = (
        inventory.total_copies -
        inventory.available_copies
    )

    if inventory_data.total_copies < borrowed_copies:
        raise HTTPException(
            status_code=400,
            detail="Total copies cannot be less than borrowed copies"
        )

    inventory.total_copies = inventory_data.total_copies
    inventory.available_copies = (
        inventory_data.total_copies -
        borrowed_copies
    )

    db.commit()
    db.refresh(inventory)

    return inventory


@router.post("/{book_id}/borrow")
@limiter.limit("5/minute")
def borrow_copy(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    inventory = (
        db.query(Inventory)
        .filter(Inventory.book_id == book_id)
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found"
        )

    if inventory.available_copies <= 0:
        raise HTTPException(
            status_code=400,
            detail="No copies available"
        )

    inventory.available_copies -= 1

    db.commit()
    db.refresh(inventory)

    return {
        "message": "Book copy allocated successfully",
        "book_id": book_id,
        "available_copies": inventory.available_copies
    }


@router.post("/{book_id}/return")
@limiter.limit("5/minute")
def return_copy(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    inventory = (
        db.query(Inventory)
        .filter(Inventory.book_id == book_id)
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found"
        )

    if inventory.available_copies >= inventory.total_copies:
        raise HTTPException(
            status_code=400,
            detail="All copies are already available"
        )

    inventory.available_copies += 1

    db.commit()
    db.refresh(inventory)

    return {
        "message": "Book copy returned successfully",
        "book_id": book_id,
        "available_copies": inventory.available_copies
    }


@router.delete("/{book_id}")
@limiter.limit("5/minute")
def delete_inventory(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):

    inventory = (
        db.query(Inventory)
        .filter(Inventory.book_id == book_id)
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found"
        )

    if inventory.available_copies != inventory.total_copies:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete inventory while copies are borrowed"
        )

    db.delete(inventory)
    db.commit()

    return {
        "message": "Inventory deleted successfully"
    }