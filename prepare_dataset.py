import os
import shutil
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}
TARGET_LABELS = {"low", "medium", "high"}


def infer_label_from_name(file_name: str):
    lowered = file_name.lower()
    for label in TARGET_LABELS:
        if label in lowered:
            return label
    return None


def main():
    project_root = Path(__file__).resolve().parent
    dataset_root = project_root / "dataset"

    for folder in ["low", "medium", "high", "unlabeled"]:
        (dataset_root / folder).mkdir(parents=True, exist_ok=True)

    copied = {"low": 0, "medium": 0, "high": 0, "unlabeled": 0}

    audio_candidates = []

    uploads_dir = project_root / "uploads"
    if uploads_dir.exists():
        for path in uploads_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                audio_candidates.append(path)

    for path in project_root.iterdir():
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            audio_candidates.append(path)

    for source in audio_candidates:
        label = infer_label_from_name(source.name)
        target_label = label if label in TARGET_LABELS else "unlabeled"
        destination = dataset_root / target_label / source.name

        if destination.exists():
            stem = destination.stem
            suffix = destination.suffix
            index = 1
            while destination.exists():
                destination = dataset_root / target_label / f"{stem}_{index}{suffix}"
                index += 1

        shutil.copy2(source, destination)
        copied[target_label] += 1

    print("Dataset preparation complete")
    print(f"Scanned candidates: {len(audio_candidates)}")
    print(
        f"Copied -> low: {copied['low']}, medium: {copied['medium']}, high: {copied['high']}, unlabeled: {copied['unlabeled']}"
    )
    if copied["unlabeled"] > 0:
        print("Note: Move files from dataset/unlabeled into low/medium/high after manual labeling.")


if __name__ == "__main__":
    main()
