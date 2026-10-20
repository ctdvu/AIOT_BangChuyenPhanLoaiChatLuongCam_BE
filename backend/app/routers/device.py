from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..database import get_db
from ..device_adapter import adapt_device_image_fields, adapt_device_payload
from ..models import Classification, PredictionDetail
from ..predictor import ModelUnavailableError, predict
from ..schemas import ClassificationResponse, DeviceJsonPayload
from ..services.images import delete_local_image, validate_and_save_image
from ..services.responses import classification_response


router = APIRouter(prefix="/api/device", tags=["device"])


@router.post("/classifications/json", response_model=ClassificationResponse, status_code=201)
def receive_device_json(
    payload: DeviceJsonPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> ClassificationResponse:
    """Nhận JSON có URL ảnh. Server chỉ lưu URL, không tải ảnh từ Internet."""
    try:
        normalized = adapt_device_payload(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record = Classification(**normalized)
    db.add(record)
    db.commit()
    db.refresh(record)
    return classification_response(record, request)


@router.post("/classifications/image", response_model=ClassificationResponse, status_code=201)
async def receive_device_image(
    request: Request,
    image: UploadFile = File(...),
    prediction: str | None = Form(default=None),
    score: float | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ClassificationResponse:
    """Nhận multipart khi thiết bị gửi trực tiếp tệp ảnh."""
    normalized = None
    if (prediction is None) != (score is None):
        raise HTTPException(status_code=422, detail="Gửi cả prediction và score, hoặc chỉ gửi ảnh để chạy AI")
    if prediction is not None:
        try:
            normalized = adapt_device_image_fields(prediction, score)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    image_path = await validate_and_save_image(image)
    try:
        if normalized is None:
            result = await run_in_threadpool(predict, settings.upload_dir / image_path.split("/")[-1])
            normalized = adapt_device_image_fields(result["ai_class"], result["confidence"])
            normalized["prediction_detail"] = PredictionDetail(
                ai_class=result["ai_class"], probabilities=result["probabilities"]
            )
        record = Classification(image_path=image_path, **normalized)
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

