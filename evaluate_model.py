import json
import os
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from utils.voice_analyzer import extract_features


DATASET_PATH = "dataset"
MODEL_PATH = "model.pkl"
METRICS_OUTPUT_PATH = "model_metrics.json"


def load_dataset(dataset_path):
    X = []
    y = []

    for label in ["low", "medium", "high"]:
        label_folder = os.path.join(dataset_path, label)
        if not os.path.isdir(label_folder):
            continue

        for file_name in os.listdir(label_folder):
            file_path = os.path.join(label_folder, file_name)
            if not os.path.isfile(file_path):
                continue

            try:
                features = extract_features(file_path)
                X.append(features)
                y.append(label)
            except Exception as error:
                print(f"Skipping {file_path}: {error}")

    if not X:
        raise ValueError(
            "No dataset samples found. Please create dataset/low, dataset/medium, dataset/high with audio files."
        )

    return np.array(X), np.array(y)


def main():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"{MODEL_PATH} not found. Train first with: python train_model.py"
        )

    X, y = load_dataset(DATASET_PATH)

    unique_labels, counts = np.unique(y, return_counts=True)
    can_stratify = np.all(counts >= 2) and len(unique_labels) > 1

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y if can_stratify else None,
    )

    model = joblib.load(MODEL_PATH)
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    labels = ["low", "medium", "high"]
    matrix = confusion_matrix(y_test, y_pred, labels=labels)
    report_text = classification_report(y_test, y_pred, zero_division=0)
    report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    print(f"Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(report_text)
    print("Confusion Matrix (rows=true, cols=pred):")
    print(matrix)

    metrics_payload = {
        "accuracy": float(accuracy),
        "labels": labels,
        "confusion_matrix": matrix.tolist(),
        "classification_report": report_dict,
        "test_samples": int(len(y_test)),
        "stratified_split": bool(can_stratify),
    }

    with open(METRICS_OUTPUT_PATH, "w", encoding="utf-8") as metrics_file:
        json.dump(metrics_payload, metrics_file, indent=2)

    print(f"\nSaved metrics to {METRICS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
