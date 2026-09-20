from pydantic import BaseModel, ConfigDict


class InventoryCreate(BaseModel):
    book_id: int
    total_copies: int


class InventoryUpdate(BaseModel):
    total_copies: int


class InventoryResponse(BaseModel):
    id: int
    book_id: int
    total_copies: int
    available_copies: int

    model_config = ConfigDict(from_attributes=True)