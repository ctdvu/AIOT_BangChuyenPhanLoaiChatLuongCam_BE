from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClassificationImageResponse(BaseModel):
    camera_id: int
    image_url: str
    captured_at: datetime
    rotation: int
    simulation: bool
    ai_class: str
    ai_display_name: str
    grade: int
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int | None = None
    label: str
    display_name: str
    confidence: float = Field(ge=0, le=1)
    tray: int
    image_url: str
    created_at: datetime
    source: str
    grade: int
    ai_class: str | None = None
    ai_display_name: str | None = None
    probabilities: dict[str, float] | None = None
    capture_session_id: str | None = None
    capture_skew_ms: float | None = None
    aggregation_policy: str | None = None
    images: list[ClassificationImageResponse] = Field(default_factory=list)


class ClassificationPage(BaseModel):
    items: list[ClassificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CategoryStat(BaseModel):
    label: str
    display_name: str
    tray: int
    count: int


class AIClassStat(BaseModel):
    ai_class: str
    display_name: str
    grade: int
    count: int


class StatsResponse(BaseModel):
    total: int
    by_category: list[CategoryStat]
    by_ai_class: list[AIClassStat]


class ModelStatusResponse(BaseModel):
    status: str
    model: str
    device: str | None
    classes: list[str]
    detail: str | None


class DeviceJsonPayload(BaseModel):
    """Ví dụ JSON thiết bị. Sửa adapter nếu JSON thực tế có tên trường khác."""

    prediction: str
    score: float = Field(ge=0, le=1)
    image_url: str


class FruitArrivedRequest(BaseModel):
    device_id: str = Field(default="esp32-conveyor-01", max_length=64)
    auto_classify: bool = True


class SortingCompletedRequest(BaseModel):
    device_id: str = Field(default="esp32-conveyor-01", max_length=64)
    grade: int | None = Field(default=None, ge=1, le=3)
    tray: int | None = Field(default=None, ge=1, le=3)
    classification_id: int | None = None
    duration_ms: int | None = Field(default=None, ge=0)


class HardwareHeartbeatRequest(BaseModel):
    device_id: str = Field(default="esp32-conveyor-01", max_length=64)
    conveyor_state: str = Field(default="running", max_length=32)


class HardwareStatusResponse(BaseModel):
    online: bool
    device_id: str
    conveyor_state: str
    message: str
    last_event: str | None = None
    last_event_at: datetime | None = None
    last_classification_id: int | None = None
    last_grade: int | None = None
    last_tray: int | None = None
    last_label: str | None = None
    last_display_name: str | None = None
    last_ai_class: str | None = None
    last_ai_display_name: str | None = None
    last_confidence: float | None = None
    sorted_count: int = 0


# ============================================================
# CÁC SCHEMAS CHO HỆ THỐNG 3 ROLE & EC2 CLOUD
# ============================================================

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    phone: str
    is_active: bool
    created_at: datetime


class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    contact_phone: str
    description: str
    is_active: bool
    service_plan: str
    subscription_expires_at: datetime | None = None
    device_api_key: str
    bound_mac_address: str | None = None
    device_enabled: bool
    cam1_rotation: int
    cam2_rotation: int
    created_at: datetime
    days_remaining: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    farm: FarmResponse | None = None


class RegisterDealerRequest(BaseModel):
    username: str
    password: str
    full_name: str
    phone: str = ""


class CreateFarmRequest(BaseModel):
    username: str
    password: str
    full_name: str
    farm_name: str
    location: str = ""
    contact_phone: str = ""
    description: str = ""
    service_plan: str = "Gói Tiêu Chuẩn"
    subscription_days: int = 180


class UpdateFarmAdminRequest(BaseModel):
    name: str | None = None
    location: str | None = None
    contact_phone: str | None = None
    description: str | None = None
    is_active: bool | None = None
    device_enabled: bool | None = None
    service_plan: str | None = None
    extend_days: int | None = None


class UpdateFarmSelfRequest(BaseModel):
    location: str | None = None
    contact_phone: str | None = None
    description: str | None = None
    cam1_rotation: int | None = None
    cam2_rotation: int | None = None


class DealerFarmStat(BaseModel):
    farm_id: int
    farm_name: str
    location: str
    contact_phone: str
    description: str
    is_active: bool
    total_fruits: int
    grade_1_count: int
    grade_1_rate: float
    grade_2_count: int
    grade_2_rate: float
    grade_3_count: int
    spoilage_rate: float
    marketable_count: int
    marketable_rate: float
    by_ai_class: dict[str, int]
    recommendation: str  # "recommended", "consider", "high_risk", "insufficient_data"
    recommendation_label: str


class DealerFarmDetailResponse(BaseModel):
    farm: FarmResponse
    stat: DealerFarmStat
    recent_classifications: list[ClassificationResponse]


class DeviceVerifyRequest(BaseModel):
    device_api_key: str | None = None
    mac_address: str | None = None


class DeviceVerifyResponse(BaseModel):
    status: str
    farm_id: int
    farm_name: str
    service_plan: str
    subscription_expires_at: datetime | None = None
    bound_mac_address: str | None = None
    message: str



