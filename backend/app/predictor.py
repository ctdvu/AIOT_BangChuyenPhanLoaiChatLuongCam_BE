"""Reuse the handed-over inference code without changing its model or transforms."""

import importlib.util
import logging
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any

from .config import BACKEND_DIR
from .constants import AI_CLASSES, label_for_prediction

HANDOVER_DIR = BACKEND_DIR.parent / "AI_handover"
INFERENCE_LOCK = Lock()
logger = logging.getLogger(__name__)


class ModelUnavailableError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_runtime() -> tuple[Any, Any, list[str], Any]:
    """Load once per API process; class order comes from the checkpoint."""
    try:
        spec = importlib.util.spec_from_file_location(
            "orange_handover_predict", HANDOVER_DIR / "predict.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Không đọc được AI_handover/predict.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected_grades = {name: item[2] for name, item in AI_CLASSES.items()}
        if module.GRADE_MAPPING != expected_grades:
            raise RuntimeError("GRADE_MAPPING bàn giao không khớp danh mục backend")
        model, class_names, device = module.load_model()
        return module, model, class_names, device
    except Exception as exc:
        logger.exception("Không tải được mô hình AI_handover")
        raise ModelUnavailableError(
            "AI chưa sẵn sàng. Kiểm tra AI_handover/models/orange_classifier_v3_best.pth "
            "và cài backend/requirements-ai.txt trong môi trường chạy backend."
        ) from exc


def predict(image_path: Path) -> dict[str, Any]:
    with INFERENCE_LOCK:
        module, model, class_names, device = load_runtime()
        try:
            probabilities = dict(module.predict_image(image_path, model, class_names, device))
        except Exception as exc:
            logger.exception("Suy luận AI thất bại")
            raise ModelUnavailableError("Không chạy được mô hình AI trên ảnh này.") from exc
    ai_class = max(probabilities, key=probabilities.get)
    return {
        "label": label_for_prediction(ai_class),
        "confidence": probabilities[ai_class],
        "ai_class": ai_class,
        "probabilities": probabilities,
    }


def model_status() -> dict[str, Any]:
    try:
        with INFERENCE_LOCK:
            _, _, class_names, device = load_runtime()
        return {"status": "ready", "model": "EfficientNet-B0 V3", "device": str(device),
                "classes": class_names, "detail": None}
    except ModelUnavailableError as exc:
        return {"status": "unavailable", "model": "EfficientNet-B0 V3", "device": None,
                "classes": list(AI_CLASSES), "detail": str(exc)}

