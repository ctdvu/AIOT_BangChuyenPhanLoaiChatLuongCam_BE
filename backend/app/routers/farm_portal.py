from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Farm, User
from ..schemas import FarmResponse, UpdateFarmSelfRequest
from ..security import require_farm


router = APIRouter(prefix="/api/farm", tags=["farm-portal"])


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


@router.get("/me", response_model=FarmResponse)
def get_my_farm(user: User = Depends(require_farm), db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.owner_id == user.id).first()
    if not farm:
        # Nếu là admin kiểm tra hoặc chưa liên kết
        farm = db.query(Farm).first()
        if not farm:
            raise HTTPException(status_code=404, detail="Chưa có nông trại nào trong hệ thống.")
    return _farm_response(farm)


@router.put("/me", response_model=FarmResponse)
def update_my_farm(payload: UpdateFarmSelfRequest, user: User = Depends(require_farm), db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.owner_id == user.id).first()
    if not farm:
        farm = db.query(Farm).first()
        if not farm:
            raise HTTPException(status_code=404, detail="Không tìm thấy Nông trại của bạn.")

    if payload.contact_phone is not None:
        farm.contact_phone = payload.contact_phone.strip()
    if payload.location is not None:
        farm.location = payload.location.strip()
    if payload.description is not None:
        farm.description = payload.description.strip()
    if payload.cam1_rotation is not None:
        if payload.cam1_rotation in (0, 90, 180, 270):
            farm.cam1_rotation = payload.cam1_rotation
    if payload.cam2_rotation is not None:
        if payload.cam2_rotation in (0, 90, 180, 270):
            farm.cam2_rotation = payload.cam2_rotation

    db.commit()
    db.refresh(farm)
    return _farm_response(farm)
