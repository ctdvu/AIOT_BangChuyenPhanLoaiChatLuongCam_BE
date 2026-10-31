from math import ceil

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..constants import AI_CLASSES, CATEGORIES, VALID_SOURCES, ai_class_for_prediction, category_for, label_for_prediction
from ..database import get_db
from ..models import Classification, Farm, PredictionDetail
from ..predictor import ModelUnavailableError, predict
from ..schemas import ClassificationPage, ClassificationResponse, StatsResponse
from ..security import get_optional_user
from ..services.images import delete_local_image, validate_and_save_image
from ..services.responses import classification_response


router = APIRouter(prefix="/api", tags=["classifications"])


def _resolve_farm_id(request: Request, db: Session, query_farm_id: int | None = None) -> int | None:
    if query_farm_id is not None:
        return query_farm_id
    user = get_optional_user(request, db)
    if user and user.role == "farm":
        farm = db.query(Farm).filter(Farm.owner_id == user.id).first()
        if farm:
            return farm.id
    return None


@router.post("/classifications", response_model=ClassificationResponse, status_code=201)
async def create_classification(
    request: Request,
    image: UploadFile = File(...),
    label: str | None = Form(default=None),
    confidence: float | None = Form(default=None),
    source: str = Form(default="device"),
    farm_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ClassificationResponse:
    normalized_label = None
    ai_class = None
    probabilities = None
    if source not in VALID_SOURCES:
        raise HTTPException(status_code=422, detail="Nguồn kết quả không hợp lệ")
    if confidence is not None and not 0 <= confidence <= 1:
        raise HTTPException(status_code=422, detail="Độ tin cậy phải từ 0 đến 1")
    if confidence is not None and not label:
        raise HTTPException(status_code=422, detail="Không thể gửi độ tin cậy khi thiếu mã nhãn")
    if label:
        try:
            normalized_label = label_for_prediction(label)
            ai_class = ai_class_for_prediction(label)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    resolved_farm_id = _resolve_farm_id(request, db, farm_id)

    image_path = await validate_and_save_image(image)
    try:
        if normalized_label is None:
            prediction = await run_in_threadpool(predict, settings.upload_dir / image_path.split("/")[-1])
            normalized_label = str(prediction["label"])
            confidence = float(prediction["confidence"])
            ai_class = prediction["ai_class"]
            probabilities = prediction["probabilities"]
            source = "model"

        category = category_for(normalized_label)
        record = Classification(
            farm_id=resolved_farm_id,
            label=normalized_label,
            confidence=1.0 if confidence is None else confidence,
            tray=category.tray,
            image_path=image_path,
            source=source,
        )
        if ai_class:
            record.prediction_detail = PredictionDetail(ai_class=ai_class, probabilities=probabilities)
        db.add(record)
        db.commit()
        db.refresh(record)
    except ModelUnavailableError as exc:
        db.rollback()
        delete_local_image(image_path)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        delete_local_image(image_path)
        raise

    return classification_response(record, request)


@router.get("/classifications/latest", response_model=ClassificationResponse)
def latest_classification(
    request: Request,
    farm_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ClassificationResponse:
    resolved_farm_id = _resolve_farm_id(request, db, farm_id)
    stmt = select(Classification).order_by(
        Classification.created_at.desc(), Classification.id.desc()
    )
    if resolved_farm_id is not None:
        stmt = stmt.where(Classification.farm_id == resolved_farm_id)

    record = db.scalar(stmt.limit(1))
    if record is None:
        # If filtered by farm and none found, check if overall exists or raise 404
        raise HTTPException(status_code=404, detail="Chưa có kết quả phân loại")
    return classification_response(record, request)


@router.get("/classifications", response_model=ClassificationPage)
def list_classifications(
    request: Request,
    farm_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ClassificationPage:
    resolved_farm_id = _resolve_farm_id(request, db, farm_id)
    count_stmt = select(func.count()).select_from(Classification)
    list_stmt = select(Classification).order_by(
        Classification.created_at.desc(), Classification.id.desc()
    )
    if resolved_farm_id is not None:
        count_stmt = count_stmt.where(Classification.farm_id == resolved_farm_id)
        list_stmt = list_stmt.where(Classification.farm_id == resolved_farm_id)

    total = db.scalar(count_stmt) or 0
    records = db.scalars(list_stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return ClassificationPage(
        items=[classification_response(record, request) for record in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.get("/stats", response_model=StatsResponse)
def stats(
    request: Request = None,
    farm_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StatsResponse:
    resolved_farm_id = _resolve_farm_id(request, db, farm_id) if request else farm_id

    cat_stmt = select(Classification.label, func.count(Classification.id)).group_by(Classification.label)
    ai_stmt = select(PredictionDetail.ai_class, func.count(PredictionDetail.classification_id)).join(
        Classification, Classification.id == PredictionDetail.classification_id
    ).group_by(PredictionDetail.ai_class)

    if resolved_farm_id is not None:
        cat_stmt = cat_stmt.where(Classification.farm_id == resolved_farm_id)
        ai_stmt = ai_stmt.where(Classification.farm_id == resolved_farm_id)

    counts = dict(db.execute(cat_stmt).all())
    ai_counts = dict(db.execute(ai_stmt).all())

    return StatsResponse(
        total=sum(counts.values()),
        by_category=[
            {
                "label": category.label,
                "display_name": category.display_name,
                "tray": category.tray,
                "count": counts.get(category.label, 0),
            }
            for category in CATEGORIES.values()
        ],
        by_ai_class=[
            {"ai_class": name, "display_name": item[1], "grade": item[2],
             "count": ai_counts.get(name, 0)}
            for name, item in AI_CLASSES.items()
        ],
    )

