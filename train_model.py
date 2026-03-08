import os
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from utils.voice_analyzer import extract_features

MIN_SAMPLES_PER_CLASS = 5
REQUIRED_LABELS = ["low", "medium", "high"]


X = []
y = []

DATASET_PATH = "dataset"

for label in REQUIRED_LABELS:
    folder = os.path.join(DATASET_PATH, label)
    if not os.path.isdir(folder):
        continue

    for file_name in os.listdir(folder):
        file_path = os.path.join(folder, file_name)
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
        "No training samples found. Add audio files under dataset/low, dataset/medium, dataset/high"
    )

X = np.array(X)
y = np.array(y)

unique_labels, counts = np.unique(y, return_counts=True)
count_map = {str(label): int(count) for label, count in zip(unique_labels, counts)}
print(f"Class distribution: {count_map}")

missing_labels = [label for label in REQUIRED_LABELS if count_map.get(label, 0) == 0]
if missing_labels:
    raise ValueError(
        "Training blocked: missing labeled classes. "
        f"Add samples for: {', '.join(missing_labels)}"
    )

insufficient_labels = [label for label in REQUIRED_LABELS if count_map.get(label, 0) < MIN_SAMPLES_PER_CLASS]
if insufficient_labels:
    details = ", ".join(f"{label}={count_map.get(label, 0)}" for label in insufficient_labels)
    raise ValueError(
        "Training blocked: dataset too small/imbalanced for reliable results. "
        f"Need at least {MIN_SAMPLES_PER_CLASS} samples per class. Current: {details}"
    )

can_stratify = np.all(counts >= 2) and len(unique_labels) > 1

if len(y) >= 15 and len(unique_labels) > 1:
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y if can_stratify else None,
    )
else:
    X_train, y_train = X, y
    X_val, y_val = None, None

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    class_weight='balanced_subsample',
    min_samples_leaf=2,
)
model.fit(X_train, y_train)

if X_val is not None and len(X_val) > 0:
    y_pred = model.predict(X_val)
    val_accuracy = accuracy_score(y_val, y_pred)
    print(f"Validation accuracy: {val_accuracy:.4f} (samples={len(X_val)})")

joblib.dump(model, "model.pkl")

print("Model trained and saved")
