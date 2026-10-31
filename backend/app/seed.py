from datetime import datetime, timedelta, timezone
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .models import Farm, User
from .security import hash_password


def seed_database(engine, session_factory) -> None:
    # 1. Tự động kiểm tra và thêm cột farm_id vào bảng classifications nếu chưa có
    with engine.connect() as conn:
        inspector = inspect(engine)
        if "classifications" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("classifications")]
            if "farm_id" not in columns:
                try:
                    conn.execute(text("ALTER TABLE classifications ADD COLUMN farm_id INTEGER NULL"))
                    conn.commit()
                except Exception:
                    pass

    # 2. Khởi tạo tài khoản và nông trại mẫu nếu bảng users trống
    with session_factory() as db:
        if db.query(User).first() is not None:
            return

        now = datetime.now(timezone.utc)

        # Admin
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            full_name="Quản trị viên Hệ thống",
            role="admin",
            phone="0912345678",
            is_active=True,
        )
        db.add(admin)

        # Chủ Nông trại 1
        farm1_user = User(
            username="farm1",
            password_hash=hash_password("farm123"),
            full_name="Nguyễn Văn Bình (Chủ Vườn)",
            role="farm",
            phone="0987654321",
            is_active=True,
        )
        db.add(farm1_user)
        db.flush()

        farm1 = Farm(
            owner_id=farm1_user.id,
            name="Nông trại Cam Cao Phong - Hòa Bình",
            location="Thị trấn Cao Phong, Huyện Cao Phong, Hòa Bình",
            contact_phone="0987654321",
            description="Chuyên canh cam lòng vàng và cam V2 đạt chuẩn VietGAP vụ thu hoạch 2026.",
            is_active=True,
            service_plan="Gói Tiêu Chuẩn (6 tháng)",
            subscription_expires_at=now + timedelta(days=180),
            device_api_key="osk_farm_caophong_2026",
            device_enabled=True,
            cam1_rotation=0,
            cam2_rotation=0,
        )
        db.add(farm1)

        # Chủ Nông trại 2
        farm2_user = User(
            username="farm2",
            password_hash=hash_password("farm123"),
            full_name="Trần Thị Lan (Hợp tác xã)",
            role="farm",
            phone="0978112233",
            is_active=True,
        )
        db.add(farm2_user)
        db.flush()

        farm2 = Farm(
            owner_id=farm2_user.id,
            name="Nông trại Cam Sành Hàm Yên - Tuyên Quang",
            location="Xã Phù Lưu, Huyện Hàm Yên, Tuyên Quang",
            contact_phone="0978112233",
            description="Vùng trồng cam sành hữu cơ đồi núi, sản lượng lớn phục vụ siêu thị và xuất khẩu.",
            is_active=True,
            service_plan="Gói Cao Cấp (1 năm)",
            subscription_expires_at=now + timedelta(days=365),
            device_api_key="osk_farm_hamyen_2026",
            device_enabled=True,
            cam1_rotation=0,
            cam2_rotation=0,
        )
        db.add(farm2)

        # Đại lý thu mua
        dealer1 = User(
            username="dealer1",
            password_hash=hash_password("dealer123"),
            full_name="Công ty Nông sản Sạch Miền Bắc",
            role="dealer",
            phone="0909888999",
            is_active=True,
        )
        db.add(dealer1)

        db.commit()
