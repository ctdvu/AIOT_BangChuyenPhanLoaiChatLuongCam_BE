from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import CameraConfiguration, CameraOrientation
from ..predictor import ModelUnavailableError
from ..services.camera_classifications import classify_capture
from ..services.cameras import CameraError, CameraManager, parse_url
from ..services.responses import classification_response


router = APIRouter(prefix="/api/cameras", tags=["cameras"])
manager = CameraManager()
CameraId = Literal[1, 2]


class ConnectRequest(BaseModel):
    camera_id: CameraId
    url: str = Field(default="", max_length=2048)
    simulation: bool = False


class CameraRequest(BaseModel):
    camera_id: CameraId


class ConfigurationRequest(BaseModel):
    url: str = Field(max_length=2048)


class RotationRequest(BaseModel):
    rotation: Literal[0, 90, 180, 270]


def camera_or_404(camera_id):
    try:
        return manager.get(camera_id)
    except CameraError as exc:
        raise HTTPException(404, str(exc)) from exc


def save_url(db, camera_id, url):
    record = db.get(CameraConfiguration, camera_id)
    if record is None:
        record = CameraConfiguration(camera_id=camera_id, url=url)
        db.add(record)
    else:
        record.url = url
    db.commit()


def restore_orientations(db):
    rotations = {record.camera_id: record.rotation for record in db.query(CameraOrientation).all()}
    for camera_id, camera in manager.cameras.items():
        camera.set_rotation(rotations.get(camera_id, 0))


@router.get("/status")
def status(db: Session = Depends(get_db)):
    records = {record.camera_id: record.url for record in db.query(CameraConfiguration).all()}
    return {"cameras": [dict(camera.snapshot(), url=records.get(camera_id, ""))
                        for camera_id, camera in manager.cameras.items()],
            "simulation_enabled": settings.camera_simulation_enabled}


@router.put("/{camera_id}/rotation")
def rotate(camera_id: int, payload: RotationRequest, db: Session = Depends(get_db)):
    camera = camera_or_404(camera_id)
    with camera.operation:
        record = db.get(CameraOrientation, camera_id)
        if record is None:
            db.add(CameraOrientation(camera_id=camera_id, rotation=payload.rotation))
        else:
            record.rotation = payload.rotation
        db.commit()
        camera.set_rotation(payload.rotation)
    return camera.snapshot()


@router.put("/{camera_id}/config")
def configure(camera_id: int, payload: ConfigurationRequest, db: Session = Depends(get_db)):
    camera_or_404(camera_id)
    url = payload.url.strip()
    try:
        if url:
            parse_url(url)
        save_url(db, camera_id, url)
    except CameraError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"camera_id": camera_id, "url": url}


@router.post("/connect", status_code=202)
def connect(payload: ConnectRequest, db: Session = Depends(get_db)):
    camera = manager.get(payload.camera_id)
    try:
        if payload.simulation:
            if not settings.camera_simulation_enabled:
                raise HTTPException(403, "Mô phỏng chưa được bật bằng CAMERA_SIMULATION_ENABLED.")
        else:
            parse_url(payload.url.strip())
            save_url(db, payload.camera_id, payload.url.strip())
        orientation = db.get(CameraOrientation, payload.camera_id)
        camera.set_rotation(orientation.rotation if orientation else 0)
        result = camera.start(payload.url.strip(), payload.simulation)
        if not payload.simulation:
            result["url"] = payload.url.strip()
        return result
    except CameraError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/disconnect")
def disconnect(payload: CameraRequest):
    try:
        return manager.get(payload.camera_id).disconnect()
    except CameraError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/{camera_id}/stream")
async def stream(camera_id: int):
    import asyncio
    camera = camera_or_404(camera_id)
    state = camera.snapshot()
    if state["status"] != "Connected":
        raise HTTPException(409, state["error"] or "Camera chưa có luồng video. Hãy kết nối trước.")
    generation = state["generation"]

    async def frames():
        last = -1
        while True:
            state = camera.snapshot()
            if state["status"] != "Connected" or state["generation"] != generation:
                break
            with camera.lock:
                frame = camera.frames[-1] if camera.frames else None
            if frame and frame.sequence != last:
                last = frame.sequence
                yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                       str(len(frame.jpeg)).encode() + b"\r\n\r\n" + frame.jpeg + b"\r\n")
            await asyncio.sleep(.05)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


def capture_images(ids):
    try:
        captured = manager.capture(ids)
    except CameraError as exc:
        raise HTTPException(409, str(exc)) from exc
    session_id = uuid4().hex
    images = []
    written = []
    try:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        for camera_id, frame in captured.items():
            filename = f"camera-{camera_id}-{session_id}.jpg"
            destination = settings.upload_dir / filename
            written.append(destination)
            destination.write_bytes(frame.jpeg)
            images.append({"camera_id": camera_id, "timestamp": frame.timestamp,
                           "image_url": f"/uploads/{filename}",
                           "simulation": frame.simulation, "rotation": frame.rotation})
    except OSError as exc:
        for path in written:
            path.unlink(missing_ok=True)
        raise HTTPException(500, "Không lưu được ảnh; kiểm tra dung lượng và quyền thư mục uploads.") from exc
    times = [frame.monotonic for frame in captured.values()]
    return {"session_id": session_id, "skew_ms": round((max(times) - min(times)) * 1000, 1),
            "images": images}, captured


@router.post("/capture")
def capture_both():
    return capture_images([1, 2])[0]


@router.post("/{camera_id}/capture")
def capture_one(camera_id: int):
    camera_or_404(camera_id)
    return capture_images([camera_id])[0]


def classify_cameras(ids, request, db):
    capture = capture_images(ids)[0]
    try:
        record = classify_capture(capture, db)
    except ModelUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"capture": capture, "classification": classification_response(record, request)}


@router.post("/classify", status_code=201)
def classify_both(request: Request, db: Session = Depends(get_db)):
    return classify_cameras([1, 2], request, db)


@router.post("/{camera_id}/classify", status_code=201)
def classify_one(camera_id: int, request: Request, db: Session = Depends(get_db)):
    camera_or_404(camera_id)
    return classify_cameras([camera_id], request, db)


