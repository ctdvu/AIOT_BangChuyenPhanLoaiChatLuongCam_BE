from fastapi import APIRouter, status


router = APIRouter(prefix="/api/device/events", tags=["hardware-events"])


@router.post("/fruit-arrived", status_code=status.HTTP_202_ACCEPTED)
def fruit_arrived() -> dict[str, str]:
    """Điểm nhận tín hiệu 'có quả tới vị trí chụp' trong phiên bản phần cứng."""
    return {"status": "accepted", "event": "fruit_arrived"}


@router.post("/sorting-completed", status_code=status.HTTP_202_ACCEPTED)
def sorting_completed() -> dict[str, str]:
    """Điểm nhận tín hiệu 'đã gạt xong'; chưa điều khiển động cơ ở bản demo."""
    return {"status": "accepted", "event": "sorting_completed"}

