from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class CameraConfiguration(Base):
    __tablename__ = "camera_configurations"

    camera_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, default="")


class CameraOrientation(Base):
    __tablename__ = "camera_orientations"

    camera_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rotation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # "admin", "farm", "dealer"
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    farm: Mapped["Farm | None"] = relationship(
        "Farm", back_populates="owner", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    service_plan: Mapped[str] = mapped_column(String(64), nullable=False, default="Gói Tiêu Chuẩn")
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_api_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    bound_mac_address: Mapped[str | None] = mapped_column(String(32), nullable=True)
    device_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cam1_rotation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cam2_rotation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    owner: Mapped["User | None"] = relationship("User", back_populates="farm")
    classifications: Mapped[list["Classification"]] = relationship(
        "Classification", back_populates="farm", cascade="all, delete-orphan"
    )


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farm_id: Mapped[int | None] = mapped_column(ForeignKey("farms.id"), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    tray: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="device")
    farm: Mapped["Farm | None"] = relationship(
        "Farm", back_populates="classifications", lazy="selectin"
    )
    prediction_detail: Mapped["PredictionDetail | None"] = relationship(
        back_populates="classification", uselist=False, cascade="all, delete-orphan",
        lazy="selectin",
    )
    capture_session: Mapped["CaptureSession | None"] = relationship(
        back_populates="classification", uselist=False, cascade="all, delete-orphan",
        lazy="selectin",
    )


class PredictionDetail(Base):
    """Separate table keeps existing classification rows/schema compatible."""

    __tablename__ = "prediction_details"

    classification_id: Mapped[int] = mapped_column(
        ForeignKey("classifications.id"), primary_key=True
    )
    ai_class: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    probabilities: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    classification: Mapped[Classification] = relationship(back_populates="prediction_detail")


class CaptureSession(Base):
    __tablename__ = "capture_sessions"

    classification_id: Mapped[int] = mapped_column(ForeignKey("classifications.id"), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    skew_ms: Mapped[float] = mapped_column(Float, nullable=False)
    aggregation_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    classification: Mapped[Classification] = relationship(back_populates="capture_session")
    images: Mapped[list["CaptureImage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin",
        order_by="CaptureImage.camera_id",
    )


class CaptureImage(Base):
    __tablename__ = "capture_images"

    classification_id: Mapped[int] = mapped_column(ForeignKey("capture_sessions.classification_id"), primary_key=True)
    camera_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation: Mapped[int] = mapped_column(Integer, nullable=False)
    simulation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ai_class: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    probabilities: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    session: Mapped[CaptureSession] = relationship(back_populates="images")

