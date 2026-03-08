import librosa
import numpy as np
from pydub import AudioSegment
import os
import subprocess
import sys
from model import predict_with_details


def extract_features(file_path):
    """Extract a stable numeric feature vector from an audio file."""
    y, sr = librosa.load(file_path, sr=22050)
    if y.size == 0:
        raise ValueError("Audio file is empty")

    # Remove leading/trailing silence and normalize amplitude for stable analysis.
    y, _ = librosa.effects.trim(y, top_db=30)
    if y.size == 0:
        raise ValueError("Audio contains only silence")
    peak = float(np.max(np.abs(y)))
    if peak > 1e-6:
        y = y / peak

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
    rms = librosa.feature.rms(y=y)[0]

    centroid_values = spectral_centroid[0]
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=S.shape[0] * 2 - 2)
    tremor_mask = (freqs >= 3) & (freqs <= 10)
    tremor_energy = np.mean(S[tremor_mask, :]) if np.any(tremor_mask) else 0.0
    overall_energy = float(np.mean(S)) if S.size else 0.0
    tremor_ratio = float(tremor_energy / max(overall_energy, 1e-6))

    # Focus instability metrics on voiced/active frames to reduce silence/noise bias.
    active_threshold = max(float(np.median(rms) * 0.9), 1e-6)
    active_mask = rms > active_threshold
    if np.sum(active_mask) < 6:
        active_mask = rms > max(float(np.mean(rms) * 0.6), 1e-6)

    centroid_active = centroid_values[active_mask[: len(centroid_values)]] if centroid_values.size else centroid_values
    bandwidth_active = spectral_bandwidth[active_mask[: len(spectral_bandwidth)]] if spectral_bandwidth.size else spectral_bandwidth
    zcr_active = zero_crossing_rate[active_mask[: len(zero_crossing_rate)]] if zero_crossing_rate.size else zero_crossing_rate

    if centroid_active.size < 3:
        centroid_active = centroid_values
    if bandwidth_active.size < 3:
        bandwidth_active = spectral_bandwidth
    if zcr_active.size < 3:
        zcr_active = zero_crossing_rate

    # Pause/fluency proxy: larger ratio often indicates interruptions/hesitations.
    energy_threshold = max(float(np.percentile(rms, 35)), 1e-6)
    pause_ratio = float(np.mean(rms < energy_threshold))

    # Duration and normalized spectral-instability signals remain fast and robust.
    duration_seconds = float(librosa.get_duration(y=y, sr=sr))
    centroid_mean = float(np.mean(centroid_active)) if centroid_active.size else 0.0
    bandwidth_mean = float(np.mean(bandwidth_active)) if bandwidth_active.size else 0.0

    # Relative variation is more reliable than absolute Hz scale across speakers/devices.
    centroid_cv = float(np.std(centroid_active) / max(centroid_mean, 1e-6))
    bandwidth_cv = float(np.std(bandwidth_active) / max(bandwidth_mean, 1e-6))
    freq_instability = float(
        np.mean(np.abs(np.diff(np.log1p(np.maximum(centroid_active, 0.0)))))
    ) if centroid_active.size > 1 else 0.0

    mfcc_active = mfcc
    if mfcc.shape[1] >= len(active_mask):
        active_cols = active_mask[: mfcc.shape[1]]
        if np.sum(active_cols) >= 6:
            mfcc_active = mfcc[:, active_cols]

    features = np.array([
        float(np.mean(np.var(np.diff(mfcc_active, axis=1), axis=1))),
        float(np.mean(zcr_active)),
        float(np.std(zcr_active)),
        float(np.mean(centroid_active)) if centroid_active.size else 0.0,
        freq_instability,
        tremor_ratio,
        duration_seconds,
        pause_ratio,
        float(np.std(rms)),
        float((0.5 * centroid_cv) + (0.5 * bandwidth_cv)),
    ], dtype=np.float32)

    # Defensive cleanup so downstream model/scoring is always numerically stable.
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
    return features

class VoiceAnalyzer:
    """
    Analyzes voice audio files for neurological risk indicators
    """
    
    def __init__(self):
        # Set FFmpeg path - try to find it in PATH first
        self._setup_ffmpeg()
    
    def _setup_ffmpeg(self):
        """Setup FFmpeg paths, trying system PATH first"""
        try:
            # Try to find ffmpeg in system PATH
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                # FFmpeg is in PATH, we're good
                return
        except (FileNotFoundError, OSError):
            pass
        
        # Try common Windows installation paths
        ffmpeg_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
            r"C:\ffmpeg\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ]
        
        ffprobe_paths = [
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\ffmpeg\ffmpeg-8.0.1-full_build\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
        ]
        
        for ffmpeg_path in ffmpeg_paths:
            if os.path.isfile(ffmpeg_path):
                AudioSegment.converter = ffmpeg_path
                break
        
        for ffprobe_path in ffprobe_paths:
            if os.path.isfile(ffprobe_path):
                AudioSegment.ffprobe = ffprobe_path
                break
        
        # If still not found, warn but continue
        if not hasattr(AudioSegment, 'converter') or not AudioSegment.converter:
            print("[WARNING] FFmpeg not found. Audio format conversion may fail. Install FFmpeg for better compatibility.")
    
    def analyze(self, file_path):
        """
        Complete voice analysis pipeline
        Returns: {
            'risk_level': str,
            'risk_score': float,
            'slurring_score': float,
            'speech_delay_score': float,
            'frequency_variation_score': float,
            'tremor_score': float,
            'recommendations': str
        }
        """
        try:
            print(f"[ANALYZER] Processing: {file_path}")
            
            converted_file_path = self._ensure_loadable_audio(file_path)
            features = extract_features(converted_file_path)

            prediction_details = predict_with_details(features)
            raw_risk = prediction_details.get('label', 'Unknown')
            model_predicted_level = self._normalize_risk_label(raw_risk)
            probabilities = self._normalize_probability_keys(
                prediction_details.get('probabilities', {})
            )
            model_confidence = float(prediction_details.get('confidence') or 0.0)

            slurring_score = self._scaled_score(float(features[0]) if len(features) > 0 else 0.0, 0.004, 0.080)
            # Prefer explicit pause ratio signal when available (index 7), fallback for old vectors.
            pause_ratio = float(features[7]) if len(features) > 7 else 0.0
            speech_delay_score = self._scaled_score(pause_ratio, 0.08, 0.55)
            freq_variation_score = self._calculate_frequency_variation_score(features)
            tremor_score = self._scaled_score(float(features[5]) if len(features) > 5 else 0.0, 0.04, 0.28)

            risk_score = self._calculate_risk_score(
                risk_level=model_predicted_level,
                probabilities=probabilities,
                model_confidence=model_confidence,
                slurring_score=slurring_score,
                speech_delay_score=speech_delay_score,
                freq_variation_score=freq_variation_score,
                tremor_score=tremor_score,
            )
            # Decide level from model confidence + biomarker evidence, not score alone.
            risk_level = self._decide_final_level(
                risk_score=risk_score,
                probabilities=probabilities,
                model_confidence=model_confidence,
                slurring_score=slurring_score,
                speech_delay_score=speech_delay_score,
                freq_variation_score=freq_variation_score,
                tremor_score=tremor_score,
            )
            risk_score = self._align_score_with_level(risk_score, risk_level)
            
            recommendations = self._get_recommendations(risk_level, risk_score, model_confidence)
            
            print(f"[ANALYZER] Risk Score: {risk_score:.2f}, Level: {risk_level}")
            
            return {
                'risk_level': risk_level,
                'risk_score': round(risk_score, 2),
                'stress_level': risk_level,
                'stress_score': round(risk_score, 2),
                'slurring_score': round(slurring_score, 2),
                'speech_delay_score': round(speech_delay_score, 2),
                'frequency_variation_score': round(freq_variation_score, 2),
                'tremor_score': round(tremor_score, 2),
                'recommendations': recommendations,
                'model_confidence': round(model_confidence, 2),
                'model_predicted_level': model_predicted_level,
                'model_probabilities': {
                    'low': round(float(probabilities.get('Low', 0.0)) * 100, 2),
                    'medium': round(float(probabilities.get('Medium', 0.0)) * 100, 2),
                    'high': round(float(probabilities.get('High', 0.0)) * 100, 2),
                }
            }
            
        except Exception as e:
            print(f"[ANALYZER] Error: {str(e)}")
            return {
                'error': str(e),
                'risk_level': 'Unknown',
                'risk_score': 0,
                'stress_level': 'Unknown',
                'stress_score': 0,
            }
    
    def _ensure_loadable_audio(self, file_path):
        """Return a path that librosa can load; convert to WAV when needed."""
        try:
            librosa.load(file_path, sr=22050)
            return file_path
        except:
            try:
                audio = AudioSegment.from_file(file_path)
                wav_path = file_path + "_converted.wav"
                audio.export(wav_path, format="wav")
                return wav_path
            except Exception as e:
                raise Exception(f"Failed to load audio: {str(e)}")

    def _risk_level_to_score(self, risk_level):
        mapping = {
            "Low": 25.0,
            "Medium": 60.0,
            "High": 85.0,
        }
        return mapping.get(risk_level, 0.0)

    def _score_to_level(self, risk_score):
        if risk_score < 33:
            return "Low"
        if risk_score < 66:
            return "Medium"
        return "High"

    def _biomarker_score_to_level(self, biomarker_score):
        if biomarker_score < 40:
            return "Low"
        if biomarker_score < 68:
            return "Medium"
        return "High"

    def _align_score_with_level(self, risk_score, risk_level):
        """Keep numeric score consistent with displayed level band."""
        centers = {"Low": 20.0, "Medium": 55.0, "High": 82.0}
        target = centers.get(risk_level, 56.0)
        aligned = (0.78 * float(risk_score)) + (0.22 * target)
        return float(np.clip(aligned, 0.0, 100.0))

    def _scaled_score(self, value, low, high):
        """Map raw metric into 0-100 with calibration and clipping."""
        if high <= low:
            return 0.0
        return float(np.clip(((float(value) - float(low)) / (float(high) - float(low))) * 100.0, 0.0, 100.0))

    def _decide_final_level(
        self,
        risk_score,
        probabilities,
        model_confidence,
        slurring_score,
        speech_delay_score,
        freq_variation_score,
        tremor_score,
    ):
        """Choose robust final level to avoid chronic 'Medium' collapse."""
        biomarker_score = (
            0.32 * slurring_score
            + 0.28 * speech_delay_score
            + 0.22 * freq_variation_score
            + 0.18 * tremor_score
        )
        biomarker_level = self._biomarker_score_to_level(biomarker_score)
        metrics = [slurring_score, speech_delay_score, freq_variation_score, tremor_score]
        high_count = sum(1 for value in metrics if float(value) >= 65.0)
        low_count = sum(1 for value in metrics if float(value) <= 35.0)

        model_level = "Unknown"
        top_prob = 0.0
        if isinstance(probabilities, dict) and probabilities:
            model_level, top_prob = max(probabilities.items(), key=lambda item: float(item[1] or 0.0))
            model_level = self._normalize_risk_label(model_level)

        # Strong biomarker patterns override uncertain model behavior.
        if high_count >= 2 or biomarker_score >= 72.0:
            return "High"
        if low_count >= 3 and biomarker_score <= 38.0:
            return "Low"

        # Trust model only when confidence and top probability are both strong.
        if model_level in {"Low", "Medium", "High"} and model_confidence >= 68.0 and top_prob >= 0.58:
            return model_level

        # Otherwise rely on evidence-driven biomarker level.
        return biomarker_level if biomarker_level != "Unknown" else self._score_to_level(risk_score)

    def _calculate_frequency_variation_score(self, features):
        """
        Convert normalized instability signals into a stable 0-100 score.
        Uses short-term centroid instability + long-term relative spectral variation.
        """
        freq_instability = float(max(features[4], 0.0)) if len(features) > 4 else 0.0
        spectral_cv = float(max(features[9], 0.0)) if len(features) > 9 else 0.0

        # Piecewise-linear calibration tuned for speech recordings:
        # stable speech -> low score, unstable/noisy/prosodically erratic -> high score.
        instability_component = self._scaled_score(freq_instability, 0.015, 0.140)
        cv_component = self._scaled_score(spectral_cv, 0.080, 0.450)

        return float(np.clip((0.70 * instability_component) + (0.30 * cv_component), 0.0, 100.0))

    def _normalize_probability_keys(self, probabilities):
        normalized = {"Low": 0.0, "Medium": 0.0, "High": 0.0}
        if not isinstance(probabilities, dict):
            return normalized

        for label, prob in probabilities.items():
            key = self._normalize_risk_label(label)
            if key in normalized:
                normalized[key] = float(prob or 0.0)
        return normalized

    def _calculate_risk_score(
        self,
        risk_level,
        probabilities,
        model_confidence,
        slurring_score,
        speech_delay_score,
        freq_variation_score,
        tremor_score,
    ):
        level_centers = {"Low": 25.0, "Medium": 60.0, "High": 85.0}

        if sum(probabilities.values()) > 0:
            model_score = (
                probabilities["Low"] * level_centers["Low"]
                + probabilities["Medium"] * level_centers["Medium"]
                + probabilities["High"] * level_centers["High"]
            )
        else:
            model_score = self._risk_level_to_score(risk_level)

        biomarker_score = (
            0.32 * slurring_score
            + 0.28 * speech_delay_score
            + 0.22 * freq_variation_score
            + 0.18 * tremor_score
        )

        # Prioritize biomarkers; model only nudges the score when confidence is meaningful.
        confidence_ratio = float(np.clip((model_confidence or 0.0) / 100.0, 0.0, 1.0))
        top_prob = 0.0
        if isinstance(probabilities, dict) and probabilities:
            top_prob = float(max(probabilities.values()))
        model_weight = 0.10 + (0.35 * confidence_ratio * top_prob)  # 0.10..0.45
        biomarker_weight = 1.0 - model_weight
        blended_score = (model_weight * model_score) + (biomarker_weight * biomarker_score)
        return float(np.clip(blended_score, 0.0, 100.0))

    def _normalize_risk_label(self, label):
        cleaned = str(label).strip().lower()
        if cleaned == "low":
            return "Low"
        if cleaned == "medium":
            return "Medium"
        if cleaned == "high":
            return "High"
        return "Unknown"
    
    def _detect_slurring(self, mfcc, sr):
        """
        Detect slurring by analyzing MFCC coefficient stability
        Higher variance = more slurring
        """
        # Calculate temporal variance in MFCC
        mfcc_variance = np.var(np.diff(mfcc, axis=1), axis=1)
        slurring = np.mean(mfcc_variance)
        
        # Normalize to 0-100 scale
        slurring_score = min(100, slurring * 50)
        return slurring_score
    
    def _detect_speech_delay(self, zero_crossing_rate):
        """
        Detect speech delay by analyzing silence periods
        Longer gaps = higher speech delay score
        """
        # Find silent frames (low zero-crossing rate)
        silence_threshold = np.mean(zero_crossing_rate) * 0.5
        silent_frames = np.sum(zero_crossing_rate < silence_threshold)
        total_frames = len(zero_crossing_rate)
        
        silence_ratio = (silent_frames / total_frames) * 100 if total_frames > 0 else 0
        
        # Map silence ratio to delay score
        speech_delay_score = min(100, silence_ratio * 1.5)
        return speech_delay_score
    
    def _detect_frequency_variation(self, spectral_centroid, sr):
        """
        Detect frequency variation by analyzing spectral changes
        Higher variation = more instability
        """
        centroid_diff = np.diff(spectral_centroid[0])
        frequency_variation = np.std(centroid_diff)
        
        # Normalize to 0-100 scale
        freq_var_score = min(100, (frequency_variation / sr) * 100)
        return freq_var_score
    
    def _detect_tremor(self, y, sr):
        """
        Detect tremor by analyzing low-frequency oscillations (3-10 Hz)
        """
        # Compute magnitude spectrogram
        S = np.abs(librosa.stft(y))
        
        # Focus on low frequencies (tremor range: 3-10 Hz)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=S.shape[0] * 2 - 2)
        tremor_mask = (freqs >= 3) & (freqs <= 10)
        tremor_energy = np.mean(S[tremor_mask, :])
        
        # Normalize to 0-100 scale
        tremor_score = min(100, tremor_energy * 200)
        return tremor_score
    
    def _get_recommendations(self, risk_level, risk_score, model_confidence=0.0):
        """Generate recommendations based on risk level"""
        if risk_level == "High":
            return (
                f"Risk Score: {risk_score:.1f}% (model confidence: {model_confidence:.1f}%). "
                "URGENT: Please consult a neurologist immediately. "
                "Symptoms suggest potential neurological concerns. "
                "Book an appointment with a specialist."
            )
        elif risk_level == "Medium":
            return (
                f"Risk Score: {risk_score:.1f}% (model confidence: {model_confidence:.1f}%). "
                "CAUTION: Some neurological indicators detected. "
                "Schedule a check-up with your doctor within 1-2 weeks. "
                "Monitor for any changes in speech or movement."
            )
        else:
            return (
                f"Risk Score: {risk_score:.1f}% (model confidence: {model_confidence:.1f}%). "
                "NORMAL: Your voice assessment appears normal. "
                "No immediate concerns detected. "
                "Regular monitoring recommended for long-term health tracking."
            )
