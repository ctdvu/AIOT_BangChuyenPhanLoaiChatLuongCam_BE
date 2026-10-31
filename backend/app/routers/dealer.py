from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Classification, Farm, User
from ..schemas import DealerFarmDetailResponse, DealerFarmStat, FarmResponse
from ..security import require_dealer
from ..services.responses import classification_response


router = APIRouter(prefix="/api/dealer", tags=["dealer"])


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


def compute_farm_stat(farm: Farm, db: Session, days: int = 30) -> DealerFarmStat:
    query = db.query(Classification).filter(Classification.farm_id == farm.id)
    if days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(Classification.created_at >= cutoff)

    items = query.all()
    total = len(items)
    g1 = sum(1 for c in items if c.tray == 1)
    g2 = sum(1 for c in items if c.tray == 2)
    g3 = sum(1 for c in items if c.tray == 3)

    g1_rate = round(g1 / total, 3) if total > 0 else 0.0
    g2_rate = round(g2 / total, 3) if total > 0 else 0.0
    spoilage_rate = round(g3 / total, 3) if total > 0 else 0.0
    marketable_count = g1 + g2
    marketable_rate = round(marketable_count / total, 3) if total > 0 else 0.0

    by_ai = {
        "fresh_orange": 0,
        "blackspotted_orange": 0,
        "cankered_orange": 0,
        "green_orange": 0,
        "rotten_orange": 0,
    }
    for c in items:
        if c.prediction_detail and c.prediction_detail.ai_class in by_ai:
            by_ai[c.prediction_detail.ai_class] += 1

    if total < 5:
        recommendation = "insufficient_data"
        rec_label = "Chưa Đủ Dữ Liệu Khảo Sát"
    elif spoilage_rate <= 0.15 and g1_rate >= 0.50:
        recommendation = "recommended"
        rec_label = "Đề Xuất Nhập (Chất Lượng Tốt)"
    elif spoilage_rate <= 0.30:
        recommendation = "consider"
        rec_label = "Cân Nhắc / Chọn Lọc Theo Lô"
    else:
        recommendation = "high_risk"
        rec_label = "Cảnh Báo Tỉ Lệ Hỏng Cao"

    return DealerFarmStat(
        farm_id=farm.id,
        farm_name=farm.name,
        location=farm.location,
        contact_phone=farm.contact_phone,
        description=farm.description,
        is_active=farm.is_active,
        total_fruits=total,
        grade_1_count=g1,
        grade_1_rate=g1_rate,
        grade_2_count=g2,
        grade_2_rate=g2_rate,
        grade_3_count=g3,
        spoilage_rate=spoilage_rate,
        marketable_count=marketable_count,
        marketable_rate=marketable_rate,
        by_ai_class=by_ai,
        recommendation=recommendation,
        recommendation_label=rec_label,
    )


@router.get("/farms", response_model=list[DealerFarmStat])
def list_farms_for_dealer(
    days: int = Query(default=30, ge=0, le=365),
    _dealer: User = Depends(require_dealer),
    db: Session = Depends(get_db),
):
    farms = db.query(Farm).filter(Farm.is_active.is_(True)).all()
    return [compute_farm_stat(f, db, days=days) for f in farms]


@router.get("/farms/{farm_id}", response_model=DealerFarmDetailResponse)
def get_farm_detail_for_dealer(
    farm_id: int,
    request: Request,
    days: int = Query(default=30, ge=0, le=365),
    _dealer: User = Depends(require_dealer),
    db: Session = Depends(get_db),
):
    farm = db.get(Farm, farm_id)
    if not farm or not farm.is_active:
        raise HTTPException(status_code=404, detail="Không tìm thấy Nông trại hoặc nông trại chưa kích hoạt.")

    stat = compute_farm_stat(farm, db, days=days)
    recent_query = db.query(Classification).filter(Classification.farm_id == farm.id)
    recent_items = recent_query.order_by(Classification.created_at.desc()).limit(12).all()

    return DealerFarmDetailResponse(
        farm=_farm_response(farm),
        stat=stat,
        recent_classifications=[classification_response(item, request) for item in recent_items],
    )
