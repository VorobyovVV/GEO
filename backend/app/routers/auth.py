from datetime import timedelta

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import get_settings
from app.db import get_db_conn
from app.deps import create_access_token, get_current_user, get_password_hash, verify_password
from app.schemas import Token, UserCreate, UserOut
from app.services.users import get_user_by_username

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
admin_whitelist = {u.strip().lower() for u in settings.admin_users.split(",") if u.strip()}


@router.post("/signup", response_model=Token, status_code=201)
def signup(payload: UserCreate):
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        existing = get_user_by_username(conn, payload.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        hashed = get_password_hash(payload.password)
        role = "admin" if payload.username.lower() in admin_whitelist else "user"
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id;",
            (payload.username, hashed, role),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=settings.jwt_expires_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    with get_db_conn() as conn:
        user = get_user_by_username(conn, form_data.username)
        if user is None or not verify_password(form_data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=settings.jwt_expires_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def read_users_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user.get("role"),
        "created_at": current_user.get("created_at"),
    }

