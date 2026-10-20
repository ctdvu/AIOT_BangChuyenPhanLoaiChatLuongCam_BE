from dataclasses import dataclass


@dataclass(frozen=True)
class OrangeCategory:
    label: str
    display_name: str
    tray: int
    description: str


CATEGORIES: dict[str, OrangeCategory] = {
    "CAM_DEP": OrangeCategory(
        label="CAM_DEP",
        display_name="Loại 1 – Cam tươi",
        tray=1,
        description="fresh_orange: cam tươi, tương ứng Grade 1 của mô hình bàn giao.",
    ),
    "CAM_KHUYET_TAT": OrangeCategory(
        label="CAM_KHUYET_TAT",
        display_name="Loại 2 – Cam có khuyết tật",
        tray=2,
        description="blackspotted_orange hoặc cankered_orange: cam đốm đen hoặc loét vỏ.",
    ),
    "CAM_HONG": OrangeCategory(
        label="CAM_HONG",
        display_name="Loại 3 – Cam xanh hoặc thối",
        tray=3,
        description="green_orange hoặc rotten_orange: cam xanh hoặc thối, tương ứng Grade 3.",
    ),
}

VALID_SOURCES = {"simulation", "model", "device"}

# (internal grade label, Vietnamese class name, handover grade)
AI_CLASSES = {
    "blackspotted_orange": ("CAM_KHUYET_TAT", "Cam đốm đen", 2),
    "cankered_orange": ("CAM_KHUYET_TAT", "Cam loét vỏ", 2),
    "fresh_orange": ("CAM_DEP", "Cam tươi", 1),
    "green_orange": ("CAM_HONG", "Cam xanh", 3),
    "rotten_orange": ("CAM_HONG", "Cam thối", 3),
}


def label_for_prediction(prediction: str) -> str:
    value = prediction.strip()
    if value.lower() in AI_CLASSES:
        return AI_CLASSES[value.lower()][0]
    return category_for(value.upper()).label


def ai_class_for_prediction(prediction: str) -> str | None:
    value = prediction.strip().lower()
    return value if value in AI_CLASSES else None


def category_for(label: str) -> OrangeCategory:
    try:
        return CATEGORIES[label]
    except KeyError as exc:
        raise ValueError(f"Mã nhãn không hợp lệ: {label}") from exc

