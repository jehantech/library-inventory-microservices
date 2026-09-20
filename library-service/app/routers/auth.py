from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ..security import create_access_token


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


fake_user = {
    "username": "librarian",
    "password": "library123"
}


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):

    if form_data.username != fake_user["username"]:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if form_data.password != fake_user["password"]:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        data={"sub": form_data.username}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }