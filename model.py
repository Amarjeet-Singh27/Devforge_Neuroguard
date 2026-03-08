import os
import joblib
import numpy as np


MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

try:
    model = joblib.load(MODEL_PATH)
except Exception:
    model = None


def predict(features):
    details = predict_with_details(features)
    return details["label"]


def predict_with_details(features):
    if model is None:
        raise FileNotFoundError(
            f"Model file not found or invalid at: {MODEL_PATH}. "
            "Train the model first by running train_model.py"
        )

    features_array = np.asarray(features, dtype=np.float32).reshape(1, -1)
    expected = getattr(model, "n_features_in_", None)
    if expected is not None and features_array.shape[1] != int(expected):
        if features_array.shape[1] > int(expected):
            features_array = features_array[:, : int(expected)]
        else:
            pad_width = int(expected) - features_array.shape[1]
            features_array = np.pad(features_array, ((0, 0), (0, pad_width)), mode="constant")

    prediction = str(model.predict(features_array)[0])
    probabilities = {}

    if hasattr(model, "predict_proba") and hasattr(model, "classes_"):
        raw_probs = model.predict_proba(features_array)[0]
        probabilities = {
            str(label): float(prob)
            for label, prob in zip(model.classes_, raw_probs)
        }

    confidence = 0.0
    if probabilities:
        sorted_probs = sorted(probabilities.values(), reverse=True)
        top_prob = sorted_probs[0]
        second_prob = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
        margin = top_prob - second_prob
        confidence = float(np.clip((0.6 * top_prob + 0.4 * margin) * 100.0, 0.0, 100.0))

    return {
        "label": prediction,
        "probabilities": probabilities,
        "confidence": round(confidence, 2),
    }
