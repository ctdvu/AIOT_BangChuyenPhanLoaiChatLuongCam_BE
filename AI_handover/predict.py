"""Run with: python predict.py path/to/image.jpg [path/to/another.png]"""

import argparse
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms


PROJECT_DIR = Path(__file__).resolve().parent
CHECKPOINT_PATH = PROJECT_DIR / "models" / "orange_classifier_v3_best.pth"
EXPECTED_CLASSES = [
    "blackspotted_orange",
    "cankered_orange",
    "fresh_orange",
    "green_orange",
    "rotten_orange",
]
GRADE_MAPPING = {
    "fresh_orange": 1,
    "blackspotted_orange": 2,
    "cankered_orange": 2,
    "green_orange": 3,
    "rotten_orange": 3,
}
PREPROCESSING = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


def load_model() -> tuple[nn.Module, list[str], torch.device]:
    checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
    if "model_state_dict" not in checkpoint:
        raise KeyError("Checkpoint thiếu model_state_dict.")

    class_names = list(checkpoint.get("class_names", EXPECTED_CLASSES))
    if len(class_names) != 5 or set(class_names) != set(EXPECTED_CLASSES):
        raise ValueError(f"Checkpoint class_names không đúng 5 lớp mong đợi: {class_names}")

    if "class_to_idx" in checkpoint:
        expected_indices = {name: index for index, name in enumerate(class_names)}
        if checkpoint["class_to_idx"] != expected_indices:
            raise ValueError("Checkpoint class_to_idx không khớp thứ tự class_names.")

    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 5)
    model.load_state_dict(checkpoint["model_state_dict"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    return model, class_names, device


def predict_image(
    image_path: Path, model: nn.Module, class_names: list[str], device: torch.device
) -> list[tuple[str, float]]:
    with Image.open(image_path) as image:
        image_tensor = PREPROCESSING(image.convert("RGB")).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(image_tensor)
        probabilities = torch.softmax(logits, dim=1)[0].cpu().tolist()

    return list(zip(class_names, probabilities))


def main() -> None:
    parser = argparse.ArgumentParser(description="Phân loại cam bằng model V3.")
    parser.add_argument("images", nargs="+", type=Path, help="Đường dẫn ảnh cần dự đoán")
    args = parser.parse_args()
    for path in args.images:
        if not path.is_file():
            parser.error(f"Không tìm thấy ảnh: {path}")
    model, class_names, device = load_model()

    for image_path in args.images:
        probabilities = predict_image(image_path, model, class_names, device)
        ranked = sorted(probabilities, key=lambda item: item[1], reverse=True)
        predicted_class, confidence = ranked[0]

        print("=" * 36)
        print(f"Image: {image_path.name}")
        print("\nPrediction:")
        print(f"Class: {predicted_class}")
        print(f"Confidence: {confidence:.2%}")
        print(f"\nGrade: Grade {GRADE_MAPPING[predicted_class]}")
        print("\nProbabilities:")
        for class_name, probability in probabilities:
            print(f"{class_name}: {probability:.2%}")
        print()
        for rank, (class_name, probability) in enumerate(ranked[:3], start=1):
            print(f"Top {rank}: {class_name} ({probability:.2%})")
        print("=" * 21)


if __name__ == "__main__":
    main()
