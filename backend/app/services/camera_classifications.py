"""One fruit/classification row with one or two independently predicted views."""

from datetime import datetime

from ..config import settings
from ..constants import category_for
from ..models import CaptureImage, CaptureSession, Classification, PredictionDetail
from ..predictor import ModelUnavailableError, predict
from .images import delete_local_image


def classify_capture(capture, db):
    images = capture["images"]
    try:
        predictions = []
        for image in images:
            image_path = image["image_url"].lstrip("/")
            try:
                prediction = predict(settings.upload_dir / image_path.split("/")[-1])
            except ModelUnavailableError as exc:
                raise ModelUnavailableError(
                    f"Không phân loại được Camera {image['camera_id']}: {exc} "
                    "Chưa lưu lượt này vào lịch sử; hãy thử chụp và phân loại lại."
                ) from exc
            predictions.append(prediction)

        # Preserve defects visible in either view. On the same grade, use the
        # more confident prediction. This is application logic, not a new model.
        selected = max(predictions, key=lambda result: (
            category_for(result["label"]).tray, result["confidence"],
        ))
        record = Classification(
            label=selected["label"], confidence=selected["confidence"],
            tray=category_for(selected["label"]).tray,
            image_path=images[0]["image_url"].lstrip("/"), source="model",
            prediction_detail=PredictionDetail(
                ai_class=selected["ai_class"], probabilities=selected["probabilities"],
            ),
            capture_session=CaptureSession(
                session_id=capture["session_id"], skew_ms=capture["skew_ms"],
                aggregation_policy="worst_grade" if len(images) == 2 else "single_view",
                images=[CaptureImage(
                    camera_id=image["camera_id"], image_path=image["image_url"].lstrip("/"),
                    captured_at=datetime.fromisoformat(image["timestamp"]),
                    rotation=image["rotation"], simulation=image["simulation"],
                    ai_class=prediction["ai_class"], confidence=prediction["confidence"],
                    probabilities=prediction["probabilities"],
                ) for image, prediction in zip(images, predictions)],
            ),
        )
        db.add(record)
        db.flush()
        db.refresh(record)
        db.commit()
        return record
    except Exception:
        db.rollback()
        for image in images:
            delete_local_image(image["image_url"].lstrip("/"))
        raise
