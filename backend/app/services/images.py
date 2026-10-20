from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from ..config import settings


ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


async def validate_and_save_image(image: UploadFile) -> str:
    data = await image.read(settings.max_image_size_mb * 1024 * 1024 + 1)
    if not data:
        raise HTTPException(status_code=422, detail="Tệp ảnh rỗng")
    if len(data) > settings.max_image_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ảnh vượt quá {settings.max_image_size_mb} MB",
        )

    try:
        with Image.open(BytesIO(data)) as parsed:
            parsed.verify()
            image_format = parsed.format
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="Tệp tải lên không phải ảnh hợp lệ")

    if image_format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=422, detail="Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{ALLOWED_FORMATS[image_format]}"
    destination = settings.upload_dir / filename
    destination.write_bytes(data)
    return f"uploads/{filename}"


def delete_local_image(image_path: str) -> None:
    if not image_path.startswith("uploads/"):
        return
    candidate = (settings.upload_dir / Path(image_path).name).resolve()
    upload_root = settings.upload_dir.resolve()
    if candidate.parent == upload_root and candidate.exists():
        candidate.unlink()

