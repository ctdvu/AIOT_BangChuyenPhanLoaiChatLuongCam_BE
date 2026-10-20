from typing import Any

from .constants import ai_class_for_prediction, category_for, label_for_prediction
from .models import PredictionDetail


def adapt_device_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Đổi JSON bên ngoài sang cấu trúc nội bộ ổn định.

    Ví dụ hiện tại:
      prediction -> label
      score      -> confidence
      image_url  -> image_path

    Khi nhóm phần cứng chốt JSON, chỉ sửa ánh xạ trong hàm này (hoặc router
    nhận thiết bị), không cần đổi database và frontend.
    """
    prediction = str(payload.get("prediction", ""))
    confidence = payload.get("score")
    image_path = str(payload.get("image_url", "")).strip()

    normalized = adapt_device_image_fields(prediction, confidence)
    if not image_path.startswith(("http://", "https://")):
        raise ValueError("image_url phải bắt đầu bằng http:// hoặc https://")

    return {
        **normalized,
        "image_path": image_path,
    }


def adapt_device_image_fields(prediction: str, score: float) -> dict[str, Any]:
    """Chuẩn hóa metadata khi thiết bị gửi trực tiếp tệp ảnh multipart."""
    category = category_for(label_for_prediction(prediction))
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError("score phải là một số từ 0 đến 1")
    if not 0 <= score <= 1:
        raise ValueError("score phải nằm trong khoảng 0 đến 1")
    normalized = {
        "label": category.label,
        "confidence": score,
        "tray": category.tray,
        "source": "device",
    }
    ai_class = ai_class_for_prediction(prediction)
    if ai_class:
        normalized["prediction_detail"] = PredictionDetail(ai_class=ai_class)
    return normalized

