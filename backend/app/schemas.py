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

