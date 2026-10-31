import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Farm, User


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(derived.hex(), hash_hex)
    except Exception:
        return False


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_access_token(user_id: int, username: str, role: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    exp = int(time.time()) + (settings.access_token_expire_hours * 3600)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": exp,
    }
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header_b64 = _b64encode(header_bytes)
    payload_b64 = _b64encode(payload_bytes)
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(settings.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Token không đúng định dạng.")
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(settings.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Chữ ký token không hợp lệ.")
        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token đã hết hạn.")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Xác thực thất bại: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def generate_device_api_key() -> str:
    return f"osk_farm_{secrets.token_hex(16)}"


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", 0))
        user = db.get(User, user_id)
        if user and user.is_active:
            return user
    except HTTPException:
        return None
    return None


def require_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập để thực hiện hành động này.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: User = Depends(require_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Admin mới có quyền truy cập.")
    return user


def require_farm(user: User = Depends(require_current_user)) -> User:
    if user.role not in ("farm", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Chủ Nông Trại mới có quyền truy cập.")
    return user


def require_dealer(user: User = Depends(require_current_user)) -> User:
    if user.role not in ("dealer", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Đại Lý mới có quyền truy cập.")
    return user


def require_authenticated_farm_device(request: Request, db: Session = Depends(get_db)) -> Farm:
    """Xác thực thiết bị ESP32 thông qua header X-Device-Key và X-Device-MAC."""
    api_key = request.headers.get("X-Device-Key") or request.query_params.get("device_api_key")
    mac_address = request.headers.get("X-Device-MAC") or request.query_params.get("device_mac")

    if not api_key:
        # Nếu đang chạy test hoặc cho phép fallback khi chưa có farm nào
        if settings.allow_unauthenticated_device_in_tests:
            farm = db.query(Farm).first()
            if farm:
                return farm
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu header X-Device-Key. Vui lòng cung cấp API Key của Nông trại.",
        )

    farm = db.query(Farm).filter(Farm.device_api_key == api_key.strip()).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key không tồn tại hoặc không khớp với Nông trại nào.",
        )

    if not farm.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nông trại này đã bị vô hiệu hóa bởi Admin.",
        )

    if not farm.device_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Thiết bị ESP32 của nông trại này đã bị khóa quyền gọi API.",
        )

    now = datetime.now(timezone.utc)
    if farm.subscription_expires_at is not None:
        sub_exp = farm.subscription_expires_at
        if sub_exp.tzinfo is None:
            sub_exp = sub_exp.replace(tzinfo=timezone.utc)
        if sub_exp < now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Gói dịch vụ của nông trại đã hết hạn vào {sub_exp.strftime('%d/%m/%Y')}. Vui lòng liên hệ Admin gia hạn.",
            )

    if mac_address:
        mac_clean = mac_address.strip().upper()
        if not farm.bound_mac_address:
            # Lần đầu kết nối -> Tự động khóa địa chỉ MAC này
            farm.bound_mac_address = mac_clean
            db.commit()
            db.refresh(farm)
        elif farm.bound_mac_address.upper() != mac_clean:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API Key này đã được khóa với mạch ESP32 khác ({farm.bound_mac_address}). Liên hệ Admin để gỡ liên kết MAC.",
            )

    return farm
