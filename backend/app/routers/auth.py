from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Farm, User
from ..schemas import FarmResponse, LoginRequest, RegisterDealerRequest, TokenResponse, UserResponse
from ..security import (
    create_access_token,
    hash_password,
    require_current_user,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _farm_response(farm: Farm | None) -> FarmResponse | None:
    if farm is None:
        return None
    days = None
    if farm.subscription_expires_at is not None:
        now = datetime.now(timezone.utc)
        sub_exp = farm.subscription_expires_at
        if sub_exp.tzinfo is None:
            sub_exp = sub_exp.replace(tzinfo=timezone.utc)
        days = max(0, (sub_exp - now).days)

    return FarmResponse(
        id=farm.id,
        name=farm.name,
        location=farm.location,
        contact_phone=farm.contact_phone,
        description=farm.description,
        is_active=farm.is_active,
        service_plan=farm.service_plan,
        subscription_expires_at=farm.subscription_expires_at,
        device_api_key=farm.device_api_key,
        bound_mac_address=farm.bound_mac_address,
        device_enabled=farm.device_enabled,
        cam1_rotation=farm.cam1_rotation,
        cam2_rotation=farm.cam2_rotation,
        created_at=farm.created_at,
        days_remaining=days,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này đã bị vô hiệu hóa bởi Admin.",
        )

    token = create_access_token(user.id, user.username, user.role)
    farm = db.query(Farm).filter(Farm.owner_id == user.id).first() if user.role == "farm" else None

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        farm=_farm_response(farm),
    )


@router.post("/register-dealer", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_dealer(payload: RegisterDealerRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tên đăng nhập đã tồn tại.")

    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role="dealer",
        phone=payload.phone.strip(),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        farm=None,
    )


@router.get("/me", response_model=TokenResponse)
def get_me(user: User = Depends(require_current_user), db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.owner_id == user.id).first() if user.role == "farm" else None
    token = create_access_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        farm=_farm_response(farm),
    )
