"""로컬 인증 엔드포인트 (회원가입 / 로그인 / 내 정보)."""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.auth import LocalAuth
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


# ── 스키마 ─────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str
    gender: str = "N"   # M / F / N

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-z0-9_]{4,20}$', v):
            raise ValueError("아이디는 4~20자의 영문 소문자, 숫자, 언더스코어(_)만 사용 가능합니다.")
        if v[0].isdigit():
            raise ValueError("아이디는 숫자로 시작할 수 없습니다.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError("비밀번호는 영문자를 포함해야 합니다.")
        if not re.search(r'[0-9]', v):
            raise ValueError("비밀번호는 숫자를 포함해야 합니다.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    nickname: str
    gender: str


class MeResponse(BaseModel):
    user_id: str
    username: str
    nickname: str
    gender: str


# ── 헬퍼 ──────────────────────────────────────────────────────

async def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    if not cred:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
    payload = decode_token(cred.credentials)
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 만료됐거나 유효하지 않습니다.")

    result = await db.execute(
        select(LocalAuth).where(LocalAuth.username == payload["sub"])
    )
    auth = result.scalar_one_or_none()
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다.")

    user_result = await db.execute(select(User).where(User.id == auth.user_id))
    user = user_result.scalar_one_or_none()

    return MeResponse(
        user_id=str(auth.user_id),
        username=auth.username,
        nickname=user.nickname if user else auth.username,
        gender=auth.gender,
    )


# ── 엔드포인트 ────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    dup = await db.execute(select(LocalAuth).where(LocalAuth.username == body.username))
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 아이디입니다.")

    user = User(nickname=body.nickname, gender=body.gender)
    db.add(user)
    await db.flush()

    auth = LocalAuth(
        username=body.username,
        password_hash=hash_password(body.password),
        user_id=user.id,
        gender=body.gender,
    )
    db.add(auth)
    await db.commit()

    token = create_access_token({"sub": body.username})
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        username=body.username,
        nickname=body.nickname,
        gender=body.gender,
    )


@router.post("/login", response_model=TokenResponse, summary="로그인")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(LocalAuth).where(LocalAuth.username == body.username))
    auth = result.scalar_one_or_none()

    if not auth or not verify_password(body.password, auth.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    user_result = await db.execute(select(User).where(User.id == auth.user_id))
    user = user_result.scalar_one_or_none()

    token = create_access_token({"sub": auth.username})
    return TokenResponse(
        access_token=token,
        user_id=str(auth.user_id),
        username=auth.username,
        nickname=user.nickname if user else auth.username,
        gender=auth.gender,
    )


@router.get("/me", response_model=MeResponse, summary="내 정보 조회")
async def me(current: MeResponse = Depends(get_current_user)) -> MeResponse:
    return current
