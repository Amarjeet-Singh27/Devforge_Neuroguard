import os
import librosa
import numpy as np
from pydub import AudioSegment

# 🔥 IMPORTANT: Set correct FFmpeg path
AudioSegment.converter = r"C:\ffmpeg\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
AudioSegment.ffprobe   = r"C:\ffmpeg\ffmpeg-8.0.1-full_build\bin\ffprobe.exe"


def extract_features(file_path):
    try:
        print("Processing file:", file_path)

        # Step 1: Convert any format to WAV
        audio = AudioSegment.from_file(file_path)

        wav_path = file_path + "_converted.wav"
        audio.export(wav_path, format="wav")

        print("Converted to WAV:", wav_path)

        # Step 2: Load audio using librosa
        y, sr = librosa.load(wav_path, sr=None)

        print("Audio loaded successfully")

        # Step 3: Extract MFCC features
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_scaled = np.mean(mfcc.T, axis=0)

        print("Features extracted successfully")

        return mfcc_scaled

    except Exception as e:
        print("ERROR in audio processing:", str(e))
        return None