"""One fruit/classification row with one or two independently predicted views."""

from datetime import datetime

from ..config import settings
from ..constants import category_for
from ..models import CaptureImage, CaptureSession, Classification, PredictionDetail
from ..predictor import ModelUnavailableError, predict
from .images import delete_local_image


def select_final_prediction(predictions: list[dict], gap_threshold: float = 0.20) -> tuple[dict, str]:
    """Tổng hợp kết quả phân loại từ 1 hoặc 2 góc nhìn của cùng 1 quả cam:

    - 1 ảnh: trả về kết quả góc đó (single_view).
    - 2 ảnh cùng loại (cùng grade): lấy ảnh có độ tin cậy cao hơn (same_grade_max_conf).
    - 2 ảnh khác loại:
        + Nếu chênh lệch độ tin cậy > gap_threshold (chênh lệch NHIỀU, > 20%):
          lấy góc có độ tin cậy cao hơn (high_confidence_override).
        + Nếu chênh lệch độ tin cậy <= gap_threshold (chênh lệch ÍT, <= 20%):
          lấy loại thấp hơn (tức khuyết tật hơn: Loại 3 > Loại 2 > Loại 1)
          để không bỏ sót khuyết tật (close_confidence_worse_grade).
    """
    if not predictions:
        raise ValueError("Danh sách dự đoán không được để trống.")
    if len(predictions) == 1:
        return predictions[0], "single_view"

    p1, p2 = predictions[0], predictions[1]
    g1 = category_for(p1["label"]).tray
    g2 = category_for(p2["label"]).tray

    if g1 == g2:
        selected = p1 if p1["confidence"] >= p2["confidence"] else p2
        return selected, "same_grade_max_conf"

    conf_diff = abs(p1["confidence"] - p2["confidence"])
    if conf_diff > gap_threshold:
        selected = p1 if p1["confidence"] >= p2["confidence"] else p2
        return selected, "high_confidence_override"
    else:
        selected = p1 if (g1, p1["confidence"]) >= (g2, p2["confidence"]) else p2
        return selected, "close_confidence_worse_grade"


def classify_capture(capture, db, farm_id: int | None = None, source: str = "device"):
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

        selected, policy = select_final_prediction(predictions, settings.confidence_gap_threshold)

        record = Classification(
            farm_id=farm_id,
            label=selected["label"],
            confidence=selected["confidence"],
            tray=category_for(selected["label"]).tray,
            image_path=images[0]["image_url"].lstrip("/"),
            source=source,
            prediction_detail=PredictionDetail(
                ai_class=selected["ai_class"],
                probabilities=selected["probabilities"],
            ),
            capture_session=CaptureSession(
                session_id=capture["session_id"],
                skew_ms=capture.get("skew_ms", 0.0),
                aggregation_policy=policy,
                images=[
                    CaptureImage(
                        camera_id=image["camera_id"],
                        image_path=image["image_url"].lstrip("/"),
                        captured_at=datetime.fromisoformat(image["timestamp"]),
                        rotation=image.get("rotation", 0),
                        simulation=image.get("simulation", False),
                        ai_class=prediction["ai_class"],
                        confidence=prediction["confidence"],
                        probabilities=prediction["probabilities"],
                    )
                    for image, prediction in zip(images, predictions)
                ],
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
