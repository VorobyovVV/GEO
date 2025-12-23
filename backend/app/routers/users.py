from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user.get("role"),
        "created_at": current_user.get("created_at"),
    }

