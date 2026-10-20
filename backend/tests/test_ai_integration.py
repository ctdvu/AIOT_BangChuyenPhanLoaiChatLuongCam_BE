import ast
from pathlib import Path

import pytest

from app.config import settings
from app.constants import AI_CLASSES
from app.predictor import HANDOVER_DIR, ModelUnavailableError, load_runtime


@pytest.mark.parametrize("ai_class,label,grade", [
    ("fresh_orange", "CAM_DEP", 1),
    ("blackspotted_orange", "CAM_KHUYET_TAT", 2),
    ("cankered_orange", "CAM_KHUYET_TAT", 2),
    ("green_orange", "CAM_HONG", 3),
    ("rotten_orange", "CAM_HONG", 3),
])
def test_device_accepts_handover_classes(client, image_bytes, ai_class, label, grade):
    payload = {"prediction": ai_class, "score": 0.83,
               "image_url": "https://camera.example/orange.jpg"}
    json_response = client.post("/api/device/classifications/json", json=payload)
    image_response = client.post(
        "/api/device/classifications/image",
        files={"image": ("orange.jpg", image_bytes, "image/jpeg")},
        data={"prediction": f" {ai_class.upper()} ", "score": "0.83"},
    )
    for response in (json_response, image_response):
        assert response.status_code == 201, response.text
        body = response.json()
        assert (body["ai_class"], body["label"], body["grade"], body["tray"]) == (
            ai_class, label, grade, grade
        )
        assert body["probabilities"] is None  # Not supplied by the device.
    stats = client.get("/api/stats").json()
    assert stats["total"] == 2
    assert next(c for c in stats["by_ai_class"] if c["ai_class"] == ai_class)["count"] == 2


def test_backend_grade_mapping_matches_handover_source():
    tree = ast.parse((HANDOVER_DIR / "predict.py").read_text(encoding="utf-8"))
    mappings = [ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "GRADE_MAPPING" for t in node.targets)]
    assert mappings == [{name: info[2] for name, info in AI_CLASSES.items()}]


def test_ai_failure_keeps_database_and_uploads_clean(client, image_bytes, monkeypatch):
    def fail(path):
        raise ModelUnavailableError("Thiếu checkpoint")

    monkeypatch.setattr("app.routers.classifications.predict", fail)
    monkeypatch.setattr("app.routers.device.predict", fail)
    for endpoint in ("/api/classifications", "/api/device/classifications/image"):
        response = client.post(endpoint, files={"image": ("orange.jpg", image_bytes, "image/jpeg")})
        assert response.status_code == 503
        assert response.json()["detail"] == "Thiếu checkpoint"
        assert client.get("/api/stats").json()["total"] == 0
        assert list(settings.upload_dir.iterdir()) == []


def test_device_image_without_prediction_runs_ai(client, image_bytes, monkeypatch):
    probabilities = {name: 0.025 for name in AI_CLASSES}
    probabilities["green_orange"] = 0.9
    monkeypatch.setattr("app.routers.device.predict", lambda path: {
        "label": "CAM_HONG", "ai_class": "green_orange", "confidence": 0.9,
        "probabilities": probabilities,
    })
    response = client.post("/api/device/classifications/image",
                           files={"image": ("orange.jpg", image_bytes, "image/jpeg")})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source"] == "device"
    assert body["grade"] == 3
    assert body["ai_display_name"] == "Cam xanh"
    assert client.get("/api/classifications/latest").json()["probabilities"] == probabilities


@pytest.mark.parametrize("metadata", [{"prediction": "fresh_orange"}, {"score": "0.8"}])
def test_device_image_rejects_incomplete_metadata(client, image_bytes, metadata):
    response = client.post("/api/device/classifications/image",
                           files={"image": ("orange.jpg", image_bytes, "image/jpeg")}, data=metadata)
    assert response.status_code == 422
    assert list(settings.upload_dir.iterdir()) == []


def test_old_records_and_class_stats_are_compatible(client, image_bytes):
    for label in ("CAM_DEP", "green_orange"):
        response = client.post("/api/classifications",
                               files={"image": ("orange.jpg", image_bytes, "image/jpeg")},
                               data={"label": label, "confidence": "0.8", "source": "simulation"})
        assert response.status_code == 201
    history = client.get("/api/classifications").json()["items"]
    assert history[1]["ai_class"] is None
    assert history[1]["probabilities"] is None
    stats = client.get("/api/stats").json()
    assert stats["total"] == 2
    assert sum(row["count"] for row in stats["by_category"]) == 2
    assert sum(row["count"] for row in stats["by_ai_class"]) == 1


def test_real_checkpoint_matches_handover_inference(client, image_bytes):
    pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    if not (HANDOVER_DIR / "models" / "orange_classifier_v3_best.pth").exists():
        pytest.skip("Checkpoint is not installed")
    model_info = client.get("/api/model").json()
    assert model_info["status"] == "ready", model_info
    response = client.post("/api/classifications",
                           files={"image": ("orange.jpg", image_bytes, "image/jpeg")})
    assert response.status_code == 201, response.text
    body = response.json()
    module, model, class_names, device = load_runtime()
    image_path = settings.upload_dir / Path(body["image_url"]).name
    expected = dict(module.predict_image(image_path, model, class_names, device))
    assert body["probabilities"] == pytest.approx(expected, abs=1e-7)
    assert sum(body["probabilities"].values()) == pytest.approx(1.0, abs=1e-6)
    winning_class = max(expected, key=expected.get)
    assert body["ai_class"] == winning_class
    assert body["confidence"] == pytest.approx(expected[winning_class])
    assert body["grade"] == AI_CLASSES[winning_class][2]
