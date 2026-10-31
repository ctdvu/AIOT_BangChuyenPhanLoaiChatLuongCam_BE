from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Classification, Farm, User
from ..schemas import CreateFarmRequest, FarmResponse, UpdateFarmAdminRequest, UserResponse
from ..security import generate_device_api_key, hash_password, require_admin


router = APIRouter(prefix="/api/admin", tags=["admin"])


def _farm_response(farm: Farm) -> FarmResponse:
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


@router.get("/farms", response_model=list[FarmResponse])
def list_farms(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    farms = db.query(Farm).order_by(Farm.created_at.desc()).all()
    return [_farm_response(farm) for farm in farms]


@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm(payload: CreateFarmRequest, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tên đăng nhập đã tồn tại.")

    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role="farm",
        phone=payload.contact_phone.strip(),
        is_active=True,
    )
    db.add(user)
    db.flush()

    now = datetime.now(timezone.utc)
    sub_exp = now + timedelta(days=max(1, payload.subscription_days))
    api_key = generate_device_api_key()

    farm = Farm(
        owner_id=user.id,
        name=payload.farm_name.strip(),
        location=payload.location.strip(),
        contact_phone=payload.contact_phone.strip(),
        description=payload.description.strip(),
        is_active=True,
        service_plan=payload.service_plan.strip(),
        subscription_expires_at=sub_exp,
        device_api_key=api_key,
        device_enabled=True,
        cam1_rotation=0,
        cam2_rotation=0,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return _farm_response(farm)


@router.put("/farms/{farm_id}", response_model=FarmResponse)
def update_farm(farm_id: int, payload: UpdateFarmAdminRequest, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Không tìm thấy Nông trại.")

    if payload.name is not None:
        farm.name = payload.name.strip()
    if payload.location is not None:
        farm.location = payload.location.strip()
    if payload.contact_phone is not None:
        farm.contact_phone = payload.contact_phone.strip()
    if payload.description is not None:
        farm.description = payload.description.strip()
    if payload.is_active is not None:
        farm.is_active = payload.is_active
    if payload.device_enabled is not None:
        farm.device_enabled = payload.device_enabled
    if payload.service_plan is not None:
        farm.service_plan = payload.service_plan.strip()
    if payload.extend_days is not None and payload.extend_days > 0:
        base_time = farm.subscription_expires_at or datetime.now(timezone.utc)
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if base_time < now:
            base_time = now
        farm.subscription_expires_at = base_time + timedelta(days=payload.extend_days)

    db.commit()
    db.refresh(farm)
    return _farm_response(farm)


@router.post("/farms/{farm_id}/rotate-key", response_model=FarmResponse)
def rotate_farm_key(farm_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Không tìm thấy Nông trại.")
    farm.device_api_key = generate_device_api_key()
    farm.bound_mac_address = None
    db.commit()
    db.refresh(farm)
    return _farm_response(farm)


@router.post("/farms/{farm_id}/reset-mac", response_model=FarmResponse)
def reset_farm_mac(farm_id: int, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Không tìm thấy Nông trại.")
    farm.bound_mac_address = None
    db.commit()
    db.refresh(farm)
    return _farm_response(farm)


@router.get("/users", response_model=list[UserResponse])
def list_users(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserResponse.model_validate(u) for u in users]
