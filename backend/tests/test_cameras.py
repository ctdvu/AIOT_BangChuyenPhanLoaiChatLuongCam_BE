import asyncio
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import pytest

from app.config import settings
from app.database import SessionLocal
from app.routers.cameras import manager, restore_orientations, stream
from app.services.cameras import CameraError, CameraManager, Frame, parse_url, resolve_camera


@pytest.fixture
def camera_settings(monkeypatch):
    manager.shutdown()
    monkeypatch.setattr(settings, "camera_allowed_hosts", ["127.0.0.1"])
    monkeypatch.setattr(settings, "camera_simulation_enabled", True)
    monkeypatch.setattr(settings, "camera_connect_timeout", .5)
    monkeypatch.setattr(settings, "camera_read_timeout", .5)
    monkeypatch.setattr(settings, "camera_frame_max_age", .6)
    yield
    manager.shutdown()


@pytest.fixture
def phone_server(image_bytes):
    stopped = Event()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/forbidden")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=phone")
            self.end_headers()
            try:
                while not stopped.is_set():
                    if self.path != "/stalled":
                        self.wfile.write(b"--phone\r\nContent-Type: image/jpeg\r\n\r\n" + image_bytes + b"\r\n")
                        self.wfile.flush()
                        if self.path == "/finite":
                            return
                    stopped.wait(.04)
            except (OSError, ConnectionError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    stopped.set()
    server.shutdown()
    server.server_close()
    worker.join()


def wait_state(client, camera_id, expected):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        state = client.get("/api/cameras/status").json()["cameras"][camera_id - 1]
        if state["status"] == expected:
            return state
        time.sleep(.02)
    pytest.fail(f"Camera {camera_id}: expected {expected}, got {state}")


def test_two_http_readers_capture_disconnect_reconnect_and_persist(client, camera_settings, phone_server):
    base, requests = phone_server
    for camera_id in (1, 2):
        response = client.post("/api/cameras/connect", json={"camera_id": camera_id, "url": base + "/video"})
        assert response.status_code == 202
        wait_state(client, camera_id, "Connected")
    thread = manager.get(2).thread
    assert len(requests) == 2

    async def check_two_viewers():
        viewers = [await stream(1), await stream(1)]
        for viewer in viewers:
            body = await anext(viewer.body_iterator)
            assert b"Content-Type: image/jpeg" in body and b"\xff\xd8" in body
            await viewer.body_iterator.aclose()
    asyncio.run(check_two_viewers())
    assert len(requests) == 2  # Additional viewers share the original phone reader.
    pair = client.post("/api/cameras/capture").json()
    assert len(pair["images"]) == 2
    assert pair["skew_ms"] <= settings.camera_pair_max_skew * 1000
    for image in pair["images"]:
        assert image["timestamp"].endswith("+00:00")
        assert client.get(image["image_url"]).content.startswith(b"\xff\xd8")
        assert client.post(f"/api/cameras/{image['camera_id']}/capture").status_code == 200
    assert client.post("/api/cameras/disconnect", json={"camera_id": 1}).status_code == 200
    assert manager.get(1).thread is None
    assert manager.get(1).connection is None
    assert wait_state(client, 2, "Connected")
    assert manager.get(2).thread is thread
    assert client.post("/api/cameras/capture").status_code == 409
    assert client.post("/api/cameras/1/capture").status_code == 409
    assert client.post("/api/cameras/2/capture").status_code == 200
    for _ in range(2):
        assert client.post("/api/cameras/connect", json={"camera_id": 1, "url": base + "/video"}).status_code == 202
        wait_state(client, 1, "Connected")
    manager.shutdown()
    states = client.get("/api/cameras/status").json()["cameras"]
    assert all(state["url"] == base + "/video" and state["status"] == "Disconnected" for state in states)


def test_redirect_stall_and_refused_phone(client, camera_settings, phone_server):
    base, requests = phone_server
    for path, message in (("/redirect", "chuyển hướng"), ("/stalled", "thời gian")):
        client.post("/api/cameras/connect", json={"camera_id": 1, "url": base + path})
        state = wait_state(client, 1, "Error")
        assert message in state["error"]
        assert client.post("/api/cameras/1/capture").status_code == 409
    assert "/forbidden" not in requests
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    client.post("/api/cameras/connect", json={"camera_id": 1, "url": f"http://127.0.0.1:{port}/video"})
    message = wait_state(client, 1, "Error")["error"]
    assert "từ chối" in message or "thời gian" in message


def test_phone_drops_while_other_phone_keeps_streaming(client, camera_settings, phone_server):
    base, _ = phone_server
    client.post("/api/cameras/connect", json={"camera_id": 2, "url": base + "/video"})
    wait_state(client, 2, "Connected")
    client.post("/api/cameras/connect", json={"camera_id": 1, "url": base + "/finite"})
    assert "đóng luồng" in wait_state(client, 1, "Error")["error"]
    assert wait_state(client, 2, "Connected")
    assert client.post("/api/cameras/2/capture").status_code == 200


def test_simulation_is_explicit_and_config_save(client, camera_settings, monkeypatch):
    assert client.put("/api/cameras/1/config", json={"url": "http://192.168.5.10:9090/video"}).status_code == 200
    assert client.get("/api/cameras/status").json()["cameras"][0]["status"] == "Disconnected"
    client.post("/api/cameras/connect", json={"camera_id": 1, "simulation": True})
    assert wait_state(client, 1, "Connected")["simulation"] is True
    captured = client.post("/api/cameras/1/capture").json()
    assert captured["images"][0]["simulation"] is True
    monkeypatch.setattr(settings, "camera_simulation_enabled", False)
    assert client.post("/api/cameras/connect", json={"camera_id": 2, "simulation": True}).status_code == 403
    assert client.post("/api/cameras/connect", json={"camera_id": 3, "url": "http://192.168.1.2/video"}).status_code == 422
    assert client.get("/api/cameras/3/stream").status_code == 404
    assert client.post("/api/cameras/3/capture").status_code == 404
    assert client.post("/api/cameras/connect", json={"camera_id": 2, "url": ""}).status_code == 409


@pytest.mark.parametrize("url", ["file:///tmp/a", "rtsp://192.168.1.2/video", "http://user:pass@192.168.1.2/video", "http://192.168.1.2:bad/video", "http://192.168.1.2:0/video", "http://192.168.1.2/video#x", "http://192.168.1.2/\r\nx"])
def test_url_format(url):
    with pytest.raises(CameraError):
        parse_url(url)


@pytest.mark.parametrize("host", ["8.8.8.8", "127.0.0.1", "169.254.169.254", "0.0.0.0", "224.0.0.1", "[::1]", "[::ffff:192.168.1.2]"])
def test_address_policy_blocks_non_lan(host, monkeypatch):
    monkeypatch.setattr(settings, "camera_allowed_hosts", [])
    with pytest.raises(CameraError):
        resolve_camera(f"http://{host}/video")


def test_dns_all_addresses_checked_and_pinned(monkeypatch):
    monkeypatch.setattr(settings, "camera_allowed_hosts", [])
    def answer(addresses):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 80)) for address in addresses]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: answer(["192.168.1.4", "8.8.8.8"]))
    with pytest.raises(CameraError):
        resolve_camera("http://phone.local/video")
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: answer(["192.168.1.4"]))
    assert resolve_camera("http://phone.local/video")[1] == "192.168.1.4"


def test_stale_and_skewed_frames_rejected(camera_settings):
    local = CameraManager()
    now = time.monotonic()
    for id, timestamp in ((1, now - 2), (2, now)):
        camera = local.get(id)
        camera.status = "Connected"
        camera.frames.append(Frame(b"jpeg", timestamp, "timestamp", 1))
    with pytest.raises(CameraError, match="khung hình mới"):
        local.capture([1, 2])
    assert local.get(1).snapshot()["status"] == "Error"
    assert local.get(2).snapshot()["status"] == "Connected"
    local.get(1).status = "Connected"
    local.get(1).frames.clear()
    local.get(1).frames.append(Frame(b"jpeg", time.monotonic(), "timestamp", 2))
    local.get(2).frames.clear()
    local.get(2).frames.append(Frame(b"jpeg", time.monotonic() + 1, "timestamp", 2))
    with pytest.raises(CameraError):
        local.capture([1, 2])


def test_rotation_updates_stream_capture_and_persists_without_reopening(client, camera_settings):
    import cv2
    import numpy as np

    def read_image(data):
        return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)

    for camera_id in (1, 2):
        client.post("/api/cameras/connect", json={"camera_id": camera_id, "simulation": True})
        wait_state(client, camera_id, "Connected")
    camera = manager.get(1)
    worker, generation = camera.thread, camera.generation
    for angle, shape in ((90, (640, 360)), (180, (360, 640)), (270, (640, 360)), (0, (360, 640))):
        response = client.put("/api/cameras/1/rotation", json={"rotation": angle})
        assert response.status_code == 200
        assert response.json()["rotation"] == angle
        captured = client.post("/api/cameras/1/capture").json()["images"][0]
        assert captured["rotation"] == angle
        assert read_image(client.get(captured["image_url"]).content).shape[:2] == shape
        with camera.lock:
            assert all(frame.rotation == angle for frame in camera.frames)
        time.sleep(.12)  # Frames published after the change keep the chosen orientation.
        with camera.lock:
            assert read_image(camera.frames[-1].jpeg).shape[:2] == shape
        assert camera.thread is worker and camera.generation == generation
        assert manager.get(2).rotation == 0
    client.put("/api/cameras/1/rotation", json={"rotation": 90})
    manager.shutdown()
    camera.set_rotation(0)
    with SessionLocal() as db:
        restore_orientations(db)
    assert client.get("/api/cameras/status").json()["cameras"][0]["rotation"] == 90
    assert client.put("/api/cameras/1/rotation", json={"rotation": 45}).status_code == 422
    assert client.put("/api/cameras/3/rotation", json={"rotation": 90}).status_code == 404


def test_rotation_retains_frame_age_and_correct_pixel_direction(camera_settings):
    import cv2
    import numpy as np

    camera = CameraManager().get(1)
    image = np.zeros((40, 80, 3), dtype=np.uint8)
    image[:20, :40] = (0, 0, 240)  # Red top-left should move to top-right clockwise.
    camera._publish(image)
    original = camera.frames[-1]
    camera.set_rotation(90)
    rotated = camera.frames[-1]
    assert rotated.monotonic == original.monotonic and rotated.timestamp == original.timestamp
    decoded = cv2.imdecode(np.frombuffer(rotated.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (80, 40)
    assert decoded[10, 30, 2] > 200 and decoded[60, 10, 2] < 30


def prediction_for(ai_class, confidence):
    from app.constants import AI_CLASSES
    probabilities = {name: (1 - confidence) / 4 for name in AI_CLASSES}
    probabilities[ai_class] = confidence
    return {"ai_class": ai_class, "label": AI_CLASSES[ai_class][0],
            "confidence": confidence, "probabilities": probabilities}


def start_simulated_pair(client):
    for camera_id in (1, 2):
        assert client.post("/api/cameras/connect", json={"camera_id": camera_id, "simulation": True}).status_code == 202
        wait_state(client, camera_id, "Connected")


def test_paired_classification_is_one_history_row_with_both_predictions(client, camera_settings, monkeypatch):
    from app.config import settings
    from app.models import CaptureImage, CaptureSession, Classification

    start_simulated_pair(client)
    client.put("/api/cameras/1/rotation", json={"rotation": 90})
    predictions = [prediction_for("fresh_orange", .96), prediction_for("blackspotted_orange", .72)]
    calls = []

    def predict_image(path):
        assert path.is_file()
        calls.append(path)
        return predictions[len(calls) - 1]

    monkeypatch.setattr("app.services.camera_classifications.predict", predict_image)
    response = client.post("/api/cameras/classify")
    assert response.status_code == 201, response.text
    body = response.json()
    record = body["classification"]
    assert len(calls) == 2
    assert record["capture_session_id"] == body["capture"]["session_id"]
    assert record["aggregation_policy"] == "worst_grade"
    assert record["ai_class"] == "blackspotted_orange" and record["confidence"] == .72
    assert record["grade"] == 2 and record["probabilities"] == predictions[1]["probabilities"]
    assert [image["camera_id"] for image in record["images"]] == [1, 2]
    assert [image["rotation"] for image in record["images"]] == [90, 0]
    assert [image["ai_class"] for image in record["images"]] == ["fresh_orange", "blackspotted_orange"]
    for index, image in enumerate(record["images"]):
        from datetime import datetime
        assert datetime.fromisoformat(image["captured_at"]) == datetime.fromisoformat(body["capture"]["images"][index]["timestamp"])
        assert image["simulation"] is True
        assert image["probabilities"] == predictions[index]["probabilities"]
        assert client.get(image["image_url"]).content.startswith(b"\xff\xd8")
    history = client.get("/api/classifications?page_size=1").json()
    assert history["total"] == 1 and history["total_pages"] == 1
    assert history["items"] == [record]
    assert client.get("/api/classifications/latest").json() == record
    stats = client.get("/api/stats").json()
    assert stats["total"] == 1
    assert sum(item["count"] for item in stats["by_category"]) == 1
    assert sum(item["count"] for item in stats["by_ai_class"]) == 1
    assert next(item["count"] for item in stats["by_ai_class"] if item["ai_class"] == "blackspotted_orange") == 1
    with SessionLocal() as db:
        assert db.query(Classification).count() == 1
        assert db.query(CaptureSession).count() == 1
        assert db.query(CaptureImage).count() == 2
    assert len(list(settings.upload_dir.iterdir())) == 2


def test_paired_ai_failure_rolls_back_the_entire_turn(client, camera_settings, monkeypatch):
    from app.models import CaptureImage, CaptureSession, Classification, PredictionDetail
    from app.predictor import ModelUnavailableError
    start_simulated_pair(client)
    calls = []

    def predict_image(path):
        calls.append(path)
        if len(calls) == 2:
            raise ModelUnavailableError("AI lỗi ở ảnh thứ hai")
        return prediction_for("fresh_orange", .9)

    monkeypatch.setattr("app.services.camera_classifications.predict", predict_image)
    response = client.post("/api/cameras/classify")
    assert response.status_code == 503
    assert "Camera 2" in response.json()["detail"]
    assert "Chưa lưu lượt" in response.json()["detail"]
    assert client.get("/api/classifications").json()["total"] == 0
    assert client.get("/api/stats").json()["total"] == 0
    assert list(settings.upload_dir.iterdir()) == []
    with SessionLocal() as db:
        assert all(db.query(model).count() == 0 for model in (Classification, PredictionDetail, CaptureSession, CaptureImage))


def test_no_partial_turn_if_one_camera_is_disconnected(client, camera_settings, monkeypatch):
    client.post("/api/cameras/connect", json={"camera_id": 1, "simulation": True})
    wait_state(client, 1, "Connected")
    def must_not_predict(path):
        pytest.fail("AI must not run when the second view is unavailable")
    monkeypatch.setattr("app.services.camera_classifications.predict", must_not_predict)
    assert client.post("/api/cameras/classify").status_code == 409
    assert client.get("/api/classifications").json()["total"] == 0
    assert list(settings.upload_dir.iterdir()) == []


def test_single_camera_classification_keeps_legacy_rows_compatible(client, camera_settings, monkeypatch, image_bytes):
    legacy = client.post("/api/classifications", files={"image": ("old.jpg", image_bytes, "image/jpeg")},
                         data={"label": "CAM_DEP", "confidence": .9}).json()
    assert legacy["images"] == [] and legacy["capture_session_id"] is None
    client.post("/api/cameras/connect", json={"camera_id": 2, "simulation": True})
    wait_state(client, 2, "Connected")
    monkeypatch.setattr("app.services.camera_classifications.predict", lambda path: prediction_for("green_orange", .88))
    response = client.post("/api/cameras/2/classify")
    assert response.status_code == 201, response.text
    record = response.json()["classification"]
    assert record["aggregation_policy"] == "single_view"
    assert [image["camera_id"] for image in record["images"]] == [2]
    history = client.get("/api/classifications?page_size=1").json()
    assert history["total"] == 2 and history["total_pages"] == 2
    assert history["items"] == [record]
    assert client.get("/api/classifications?page=2&page_size=1").json()["items"] == [legacy]
    assert client.get("/api/stats").json()["total"] == 2


def test_paired_database_failure_does_not_leave_orphan_files(client, camera_settings, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session
    start_simulated_pair(client)
    monkeypatch.setattr("app.services.camera_classifications.predict", lambda path: prediction_for("fresh_orange", .9))
    def fail_commit(self):
        raise SQLAlchemyError("simulated commit failure")
    monkeypatch.setattr(Session, "commit", fail_commit)
    with pytest.raises(SQLAlchemyError, match="commit failure"):
        client.post("/api/cameras/classify")
    assert client.get("/api/classifications").json()["total"] == 0
    assert list(settings.upload_dir.iterdir()) == []
