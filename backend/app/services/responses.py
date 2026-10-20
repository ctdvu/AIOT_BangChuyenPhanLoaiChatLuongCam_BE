from datetime import timezone

from fastapi import Request

from ..constants import AI_CLASSES, category_for
from ..models import Classification
from ..schemas import ClassificationImageResponse, ClassificationResponse


def image_url_for(image_path: str, request: Request) -> str:
    if image_path.startswith(("http://", "https://")):
        return image_path
    return str(request.url_for("uploads", path=image_path.removeprefix("uploads/")))


def classification_response(
    record: Classification, request: Request
) -> ClassificationResponse:
    category = category_for(record.label)
    detail = record.prediction_detail
    session = record.capture_session

    return ClassificationResponse(
        id=record.id,
        label=record.label,
        display_name=category.display_name,
        confidence=record.confidence,
        tray=record.tray,
        image_url=image_url_for(record.image_path, request),
        created_at=record.created_at,
        source=record.source,
        grade=category.tray,
        ai_class=detail.ai_class if detail else None,
        ai_display_name=AI_CLASSES[detail.ai_class][1] if detail else None,
        probabilities=detail.probabilities if detail else None,
        capture_session_id=session.session_id if session else None,
        capture_skew_ms=session.skew_ms if session else None,
        aggregation_policy=session.aggregation_policy if session else None,
        images=[ClassificationImageResponse(
            camera_id=image.camera_id,
            image_url=image_url_for(image.image_path, request),
            captured_at=image.captured_at.replace(tzinfo=timezone.utc) if image.captured_at.tzinfo is None else image.captured_at,
            rotation=image.rotation, simulation=image.simulation,
            ai_class=image.ai_class, ai_display_name=AI_CLASSES[image.ai_class][1],
            grade=AI_CLASSES[image.ai_class][2], confidence=image.confidence,
            probabilities=image.probabilities,
        ) for image in session.images] if session else [],
    )

