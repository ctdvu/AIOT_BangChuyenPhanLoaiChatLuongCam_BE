from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from ..config import settings
from ..constants import category_for
from ..database import get_db
from ..models import Farm
from ..predictor import ModelUnavailableError
from ..schemas import (
    DeviceVerifyResponse,
    FruitArrivedRequest,
    HardwareHeartbeatRequest,
    HardwareStatusResponse,
    SortingCompletedRequest,
)
from ..security import get_optional_user, require_authenticated_farm_device
from ..services.camera_classifications import classify_capture
from ..services.responses import classification_response
from . import cameras


router = APIRouter(prefix="/api/device", tags=["hardware-events"])

ONLINE_TIMEOUT_SECONDS = 60.0


class HardwareStateManager:
    def __init__(self, farm_id: int | None = None) -> None:
        self.lock = Lock()
        self.farm_id = farm_id
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.device_id = f"esp32-farm-{self.farm_id or '01'}"
            self.conveyor_state = "idle"
            self.message = "Chưa nhận tín hiệu từ mạch điều khiển băng chuyền ESP32."
            self.last_event: str | None = None
            self.last_event_at: datetime | None = None
            self.last_classification_id: int | None = None
            self.last_grade: int | None = None
            self.last_tray: int | None = None
            self.last_label: str | None = None
            self.last_display_name: str | None = None
            self.last_ai_class: str | None = None
            self.last_ai_display_name: str | None = None
            self.last_confidence: float | None = None
            self.sorted_count: int = 0
        if "multi_hardware" in globals() and multi_hardware is not None:
            for mgr in multi_hardware.managers.values():
                if mgr is not self:
                    with mgr.lock:
                        mgr.sorted_count = 0
                        mgr.conveyor_state = "idle"
                        mgr.last_event = None
                        mgr.last_event_at = None

    def record_heartbeat(self, device_id: str, conveyor_state: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with self.lock:
            self.device_id = device_id or self.device_id
            self.conveyor_state = conveyor_state or "running"
            self.last_event = "heartbeat"
            self.last_event_at = now
            if self.conveyor_state == "running":
                self.message = "Băng chuyền đang chạy — Chờ quả cam đi qua cảm biến LM393."
            elif self.conveyor_state == "stopped":
                self.message = "Băng chuyền đang dừng."
            else:
                self.message = f"ESP32 trực tuyến ({self.conveyor_state})."
        return self.snapshot()

    def record_fruit_arrived(self, device_id: str) -> None:
        now = datetime.now(timezone.utc)
        with self.lock:
            self.device_id = device_id or self.device_id
            self.conveyor_state = "inspecting"
            self.last_event = "fruit_arrived"
            self.last_event_at = now
            self.message = "Cảm biến LM393 phát hiện cam! Đang dừng băng chuyền để chụp ảnh và phân loại AI…"

    def record_classified(self, result: Any) -> None:
        now = datetime.now(timezone.utc)
        with self.lock:
            self.conveyor_state = f"sorting_tray_{result.tray}"
            self.last_event = "fruit_classified"
            self.last_event_at = now
            self.last_classification_id = result.id
            self.last_grade = result.grade
            self.last_tray = result.tray
            self.last_label = result.label
            self.last_display_name = result.display_name
            self.last_ai_class = result.ai_class
            self.last_ai_display_name = result.ai_display_name
            self.last_confidence = result.confidence
            action_desc = (
                f"Servo {result.tray} xoay 60° gạt vào Máng {result.tray}"
                if result.tray in (1, 2)
                else "Giữ Servo 0°, cho chạy thẳng vào Máng 3"
            )
            self.message = (
                f"Đã phân loại #{result.id}: {result.display_name} "
                f"({result.ai_display_name or result.label}, {round(result.confidence * 100)}%) — {action_desc}."
            )

    def record_sorting_completed(
        self,
        device_id: str,
        grade: int | None = None,
        tray: int | None = None,
        classification_id: int | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with self.lock:
            self.device_id = device_id or self.device_id
            self.conveyor_state = "running"
            self.last_event = "sorting_completed"
            self.last_event_at = now
            if grade is not None:
                self.last_grade = grade
            if tray is not None:
                self.last_tray = tray
            elif grade is not None:
                self.last_tray = grade
            if classification_id is not None:
                self.last_classification_id = classification_id
            self.sorted_count += 1
            final_tray = self.last_tray or "?"
            self.message = (
                f"Đã gạt xong quả vào Máng {final_tray} (Tổng: {self.sorted_count} quả). "
                "Băng chuyền tiếp tục chạy chờ quả tiếp theo."
            )
            return {
                "grade": self.last_grade,
                "tray": self.last_tray,
                "classification_id": self.last_classification_id,
                "sorted_count": self.sorted_count,
            }

    def snapshot(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with self.lock:
            online = (
                self.last_event_at is not None
                and (now - self.last_event_at).total_seconds() <= ONLINE_TIMEOUT_SECONDS
            )
            return {
                "online": online,
                "device_id": self.device_id,
                "conveyor_state": self.conveyor_state if online else "offline",
                "message": self.message if online else "Mạch ESP32 chưa kết nối hoặc đã ngắt kết nối.",
                "last_event": self.last_event,
                "last_event_at": self.last_event_at,
                "last_classification_id": self.last_classification_id,
                "last_grade": self.last_grade,
                "last_tray": self.last_tray,
                "last_label": self.last_label,
                "last_display_name": self.last_display_name,
                "last_ai_class": self.last_ai_class,
                "last_ai_display_name": self.last_ai_display_name,
                "last_confidence": self.last_confidence,
                "sorted_count": self.sorted_count,
            }


class MultiFarmHardwareManager:
    def __init__(self) -> None:
        self.lock = Lock()
        self.managers: dict[int | None, HardwareStateManager] = {}

    def get(self, farm_id: int | None = None) -> HardwareStateManager:
        with self.lock:
            if farm_id not in self.managers:
                self.managers[farm_id] = HardwareStateManager(farm_id)
            return self.managers[farm_id]

    def reset_all(self) -> None:
        with self.lock:
            for mgr in self.managers.values():
                mgr.reset()


hardware_state = HardwareStateManager()
multi_hardware = MultiFarmHardwareManager()


def _get_connected_camera_ids() -> list[int]:
    connected: list[int] = []
    for camera_id, camera in sorted(cameras.manager.cameras.items()):
        if camera.snapshot()["status"] == "Connected":
            connected.append(camera_id)
    return connected


def _save_rotated_frame(file_bytes: bytes, filename: str, rotation: int = 0) -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.upload_dir / filename
    if rotation in (90, 180, 270):
        try:
            import cv2
            import numpy as np

            arr = np.frombuffer(file_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                rotations = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
                rotated = cv2.rotate(img, rotations[rotation])
                ok, enc = cv2.imencode(".jpg", rotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ok:
                    destination.write_bytes(enc.tobytes())
                    return
        except Exception:
            pass
    destination.write_bytes(file_bytes)


@router.get("/status", response_model=HardwareStatusResponse)
@router.get("/events/status", response_model=HardwareStatusResponse)
def get_hardware_status(
    farm_id: int | None = Query(default=None),
    request: Request = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Trả về trạng thái trực tuyến và hoạt động hiện tại của băng chuyền ESP32."""
    current_user = get_optional_user(request, db) if request else None
    resolved_farm_id = farm_id
    if current_user and current_user.role == "farm":
        farm = db.query(Farm).filter(Farm.owner_id == current_user.id).first()
        if farm:
            resolved_farm_id = farm.id

    mgr = multi_hardware.get(resolved_farm_id)
    snapshot = mgr.snapshot()
    if not snapshot["online"] and resolved_farm_id is None:
        return hardware_state.snapshot()
    return snapshot


@router.post("/verify", response_model=DeviceVerifyResponse)
def verify_device(
    farm: Farm = Depends(require_authenticated_farm_device),
) -> dict[str, Any]:
    """Endpoint để ESP32 kiểm tra kết nối API Key và xác thực Nông trại."""
    return {
        "status": "verified",
        "farm_id": farm.id,
        "farm_name": farm.name,
        "service_plan": farm.service_plan,
        "subscription_expires_at": farm.subscription_expires_at,
        "bound_mac_address": farm.bound_mac_address,
        "message": f"Xác thực thành công Nông trại: {farm.name}. Băng chuyền sẵn sàng vận hành.",
    }


@router.post("/classify-upload", status_code=status.HTTP_201_CREATED)
async def classify_upload_from_esp32(
    request: Request,
    image_1: UploadFile = File(...),
    image_2: UploadFile | None = File(default=None),
    farm: Farm = Depends(require_authenticated_farm_device),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """ESP32 tự chụp ảnh từ Camera IP và gửi trực tiếp lên EC2 để phân loại AI."""
    session_id = uuid4().hex
    now_iso = datetime.now(timezone.utc).isoformat()
    capture_images_list = []

    # Xử lý ảnh 1
    content_1 = await image_1.read()
    if not content_1:
        raise HTTPException(status_code=400, detail="Tệp image_1 rỗng.")
    filename_1 = f"esp32-farm{farm.id}-cam1-{session_id}.jpg"
    _save_rotated_frame(content_1, filename_1, farm.cam1_rotation)
    capture_images_list.append({
        "camera_id": 1,
        "timestamp": now_iso,
        "image_url": f"/uploads/{filename_1}",
        "simulation": False,
        "rotation": farm.cam1_rotation,
    })

    # Xử lý ảnh 2 nếu có
    if image_2 is not None:
        content_2 = await image_2.read()
        if content_2:
            filename_2 = f"esp32-farm{farm.id}-cam2-{session_id}.jpg"
            _save_rotated_frame(content_2, filename_2, farm.cam2_rotation)
            capture_images_list.append({
                "camera_id": 2,
                "timestamp": now_iso,
                "image_url": f"/uploads/{filename_2}",
                "simulation": False,
                "rotation": farm.cam2_rotation,
            })

    capture = {
        "session_id": session_id,
        "skew_ms": 0.0,
        "images": capture_images_list,
    }

    try:
        record = classify_capture(capture, db, farm_id=farm.id, source="device")
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    response_obj = classification_response(record, request)

    # Cập nhật trạng thái phần cứng của Nông trại
    mgr = multi_hardware.get(farm.id)
    mgr.record_classified(response_obj)
    hardware_state.record_classified(response_obj)

    return {
        "status": "classified",
        "event": "classify_upload",
        "classification_id": response_obj.id,
        "farm_id": farm.id,
        "farm_name": farm.name,
        "grade": response_obj.grade,
        "tray": response_obj.tray,
        "label": response_obj.label,
        "display_name": response_obj.display_name,
        "ai_class": response_obj.ai_class,
        "ai_display_name": response_obj.ai_display_name,
        "confidence": response_obj.confidence,
        "aggregation_policy": record.capture_session.aggregation_policy if record.capture_session else "single_view",
        "cameras_used": [img["camera_id"] for img in capture["images"]],
        "capture": capture,
        "classification": response_obj.model_dump(mode="json"),
    }


@router.post("/events/heartbeat", response_model=HardwareStatusResponse)
def device_heartbeat(
    payload: HardwareHeartbeatRequest | None = Body(default=None),
    farm: Farm | None = Depends(require_authenticated_farm_device),
) -> dict[str, Any]:
    """Nhận tín hiệu khởi động / giữ kết nối từ ESP32."""
    device_id = payload.device_id if payload else "esp32-conveyor-01"
    conveyor_state = payload.conveyor_state if payload else "running"
    farm_id = farm.id if farm else None
    mgr = multi_hardware.get(farm_id)
    res = mgr.record_heartbeat(device_id, conveyor_state)
    hardware_state.record_heartbeat(device_id, conveyor_state)
    return res


@router.post("/events/fruit-arrived", status_code=status.HTTP_202_ACCEPTED)
def fruit_arrived(
    request: Request,
    payload: FruitArrivedRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    farm: Farm | None = Depends(require_authenticated_farm_device),
) -> dict[str, Any]:
    device_id = payload.device_id if payload else "esp32-conveyor-01"
    auto_classify = payload.auto_classify if payload is not None else True
    farm_id = farm.id if farm else None
    mgr = multi_hardware.get(farm_id)
    mgr.record_fruit_arrived(device_id)
    hardware_state.record_fruit_arrived(device_id)

    connected_ids = _get_connected_camera_ids() if auto_classify else []
    if not connected_ids:
        return {
            "status": "accepted",
            "event": "fruit_arrived",
            "grade": None,
            "tray": None,
            "detail": "Đã nhận tín hiệu cảm biến nhưng chưa có camera kết nối để tự động phân loại.",
        }

    try:
        capture = cameras.capture_images(connected_ids)[0]
        record = classify_capture(capture, db, farm_id=farm_id, source="device")
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    response_obj = classification_response(record, request)
    mgr.record_classified(response_obj)
    hardware_state.record_classified(response_obj)

    return {
        "status": "classified",
        "event": "fruit_arrived",
        "classification_id": response_obj.id,
        "grade": response_obj.grade,
        "tray": response_obj.tray,
        "label": response_obj.label,
        "display_name": response_obj.display_name,
        "ai_class": response_obj.ai_class,
        "ai_display_name": response_obj.ai_display_name,
        "confidence": response_obj.confidence,
        "cameras_used": [img["camera_id"] for img in capture["images"]],
        "capture": capture,
        "classification": response_obj.model_dump(mode="json"),
    }


@router.post("/events/sorting-completed", status_code=status.HTTP_202_ACCEPTED)
def sorting_completed(
    payload: SortingCompletedRequest | None = Body(default=None),
    farm: Farm | None = Depends(require_authenticated_farm_device),
) -> dict[str, Any]:
    device_id = payload.device_id if payload else "esp32-conveyor-01"
    grade = payload.grade if payload else None
    tray = payload.tray if payload else None
    classification_id = payload.classification_id if payload else None
    farm_id = farm.id if farm else None
    if farm_id is not None:
        summary = multi_hardware.get(farm_id).record_sorting_completed(
            device_id=device_id,
            grade=grade,
            tray=tray,
            classification_id=classification_id,
        )
        hardware_state.record_sorting_completed(
            device_id=device_id,
            grade=grade,
            tray=tray,
            classification_id=classification_id,
        )
    else:
        summary = hardware_state.record_sorting_completed(
            device_id=device_id,
            grade=grade,
            tray=tray,
            classification_id=classification_id,
        )
    return {
        "status": "accepted",
        "event": "sorting_completed",
        **summary,
    }
