import os
import tempfile
import textwrap
from datetime import datetime, timezone

import librosa
import numpy as np
from pydub import AudioSegment


def _setup_ffmpeg_for_pdf():
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


def _pdf_escape(text):
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _fmt(value):
    return f"{float(value):.4f}"


def _rgb_cmd(r, g, b, stroke=False):
    op = "RG" if stroke else "rg"
    return f"{_fmt(r)} {_fmt(g)} {_fmt(b)} {op}"


def _wrap_line(prefix, value, width=92):
    full = f"{prefix}{value}"
    return textwrap.wrap(full, width=width) or [full]


def _format_datetime_for_report(value):
    if not value:
        return "N/A"

    try:
        dt = datetime.fromisoformat(str(value))
    except Exception:
        return str(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone()
    else:
        dt = dt.astimezone()
    return dt.strftime("%Y-%m-%d %H:%M %Z")


def _build_text_lines(test):
    report = test.get("detailed_report", {})
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    test_date = _format_datetime_for_report(test.get("test_date"))

    lines = [
        "NeuroGuard Voice Stress Report",
        f"Generated: {now}",
        f"Test Date: {test_date}",
        f"Report ID: {test.get('id', 'N/A')}",
        "",
        f"Stress Level: {report.get('stress_level', test.get('stress_level', 'Unknown'))}",
        f"Stress Score: {report.get('stress_score', test.get('stress_score', 0))}%",
        (
            f"Confidence Score: {report.get('confidence_score', test.get('confidence_score', 0))}% "
            f"[{report.get('confidence_band', test.get('confidence_band', 'Low'))}]"
        ),
        "",
        "Summary:",
    ]
    lines.extend(_wrap_line("", report.get("summary", test.get("recommendations", "N/A"))))
    lines.extend(["", "Primary Concerns:"])

    concerns = report.get("primary_concerns", []) or ["None noted"]
    for item in concerns[:3]:
        lines.extend(_wrap_line("- ", item))

    lines.extend(["", "Recommended Actions:"])
    actions = report.get("recommended_actions", []) or ["Repeat screening later."]
    for item in actions[:3]:
        lines.extend(_wrap_line("- ", item))

    lines.extend(["", "Disclaimer:"])
    lines.extend(
        _wrap_line(
            "",
            report.get(
                "disclaimer",
                "This AI voice report is a screening aid, not a medical diagnosis.",
            ),
        )
    )

    return lines[:30]


def _downsample_vector(values, out_len):
    arr = np.asarray(values, dtype=np.float32).flatten()
    if arr.size == 0:
        return np.zeros(out_len, dtype=np.float32)
    if arr.size <= out_len:
        out = np.zeros(out_len, dtype=np.float32)
        out[: arr.size] = arr
        return out
    idx = np.linspace(0, arr.size - 1, out_len).astype(int)
    return arr[idx]


def _downsample_matrix(matrix, rows, cols):
    mat = np.asarray(matrix, dtype=np.float32)
    if mat.ndim != 2 or mat.size == 0:
        return np.zeros((rows, cols), dtype=np.float32)
    row_idx = np.linspace(0, mat.shape[0] - 1, rows).astype(int)
    col_idx = np.linspace(0, mat.shape[1] - 1, cols).astype(int)
    return mat[row_idx][:, col_idx]


def _resolve_audio_path(audio_path):
    if not audio_path:
        return None

    candidates = [
        audio_path,
        os.path.abspath(audio_path),
        os.path.join(os.getcwd(), audio_path),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), audio_path),
    ]

    for candidate in candidates:
        normalized = os.path.normpath(candidate)
        if os.path.exists(normalized):
            return normalized
    return None


def _load_audio_for_viz(audio_path):
    resolved = _resolve_audio_path(audio_path)
    if not resolved:
        return None, None

    try:
        y, sr = librosa.load(resolved, sr=16000, mono=True, duration=12.0)
        return y, sr
    except Exception:
        pass

    temp_wav_path = None
    try:
        _setup_ffmpeg_for_pdf()
        audio = AudioSegment.from_file(resolved)
        with tempfile.NamedTemporaryFile(suffix="_pdf_viz.wav", delete=False) as temp_file:
            temp_wav_path = temp_file.name
        audio.export(temp_wav_path, format="wav")
        y, sr = librosa.load(temp_wav_path, sr=16000, mono=True, duration=12.0)
        return y, sr
    except Exception:
        return None, None
    finally:
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except OSError:
                pass


def _extract_audio_visual_features(audio_path):
    y, sr = _load_audio_for_viz(audio_path)
    if y is None or sr is None:
        return None

    try:
        if y.size == 0:
            return None

        waveform = _downsample_vector(y, 240)
        stft = np.abs(librosa.stft(y, n_fft=512, hop_length=256))
        spectrogram = librosa.amplitude_to_db(stft + 1e-9, ref=np.max)
        spectrogram = _downsample_matrix(spectrogram, 56, 120)

        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, n_fft=512, hop_length=256)
        mfcc = _downsample_matrix(mfcc, 13, 120)

        return {
            "sample_rate": int(sr),
            "duration": float(len(y) / float(sr)),
            "waveform": waveform,
            "spectrogram": spectrogram,
            "mfcc": mfcc,
        }
    except Exception:
        return None


def _normalize_matrix(matrix):
    arr = np.asarray(matrix, dtype=np.float32)
    if arr.size == 0:
        return np.zeros_like(arr)
    min_v = float(np.min(arr))
    max_v = float(np.max(arr))
    span = max(1e-9, max_v - min_v)
    return (arr - min_v) / span


def _colormap(v):
    x = float(np.clip(v, 0.0, 1.0))
    r = x ** 0.8
    g = max(0.0, x - 0.2) ** 0.7
    b = (1.0 - x) ** 1.4
    return r, g, b


def _append_text(cmds, x, y, text, size=10, bold=False):
    font = "F2" if bold else "F1"
    escaped = _pdf_escape(text)
    cmds.append("BT")
    cmds.append(f"/{font} {size} Tf")
    cmds.append(f"{_fmt(x)} {_fmt(y)} Td")
    cmds.append(f"({escaped}) Tj")
    cmds.append("ET")


def _append_badge(cmds, x, y, w, h, text, bg, fg):
    cmds.append(_rgb_cmd(*bg))
    cmds.append(f"{_fmt(x)} {_fmt(y)} {_fmt(w)} {_fmt(h)} re f")
    _append_text(cmds, x + 7, y + h / 2 - 4, text, size=10, bold=True)
    cmds.append(_rgb_cmd(*fg))


def _append_panel(cmds, x, y, w, h, bg=(1, 1, 1), border=(0.85, 0.88, 0.94)):
    cmds.append(_rgb_cmd(*bg))
    cmds.append(f"{_fmt(x)} {_fmt(y)} {_fmt(w)} {_fmt(h)} re f")
    cmds.append(_rgb_cmd(*border, stroke=True))
    cmds.append(f"{_fmt(x)} {_fmt(y)} {_fmt(w)} {_fmt(h)} re S")


def _draw_axis_labels(cmds, x, y, w, h, x_label, y_label):
    _append_text(cmds, x + (w / 2) - 28, y - 10, x_label, size=8)
    _append_text(cmds, x + 4, y + h - 10, y_label, size=8)


def _draw_waveform(cmds, samples, x, y, w, h):
    vals = np.asarray(samples, dtype=np.float32)
    if vals.size == 0:
        return

    cmds.append(_rgb_cmd(0.03, 0.09, 0.20))
    cmds.append(f"{_fmt(x)} {_fmt(y)} {_fmt(w)} {_fmt(h)} re f")

    center_y = y + h / 2.0
    peak = float(np.max(np.abs(vals)))
    scale = (h * 0.40) / max(1e-6, peak)
    xs = np.linspace(x + 2, x + w - 2, vals.size)
    ys = center_y + vals * scale

    cmds.append(_rgb_cmd(0.18, 0.74, 0.98, stroke=True))
    cmds.append("1.2 w")
    cmds.append(f"{_fmt(xs[0])} {_fmt(ys[0])} m")
    for i in range(1, len(xs)):
        cmds.append(f"{_fmt(xs[i])} {_fmt(ys[i])} l")
    cmds.append("S")


def _draw_heatmap(cmds, matrix, x, y, w, h, flip_y=False):
    norm = _normalize_matrix(matrix)
    rows, cols = norm.shape
    if rows == 0 or cols == 0:
        return

    cell_w = w / cols
    cell_h = h / rows
    for r in range(rows):
        src_r = rows - 1 - r if flip_y else r
        for c in range(cols):
            rv, gv, bv = _colormap(float(norm[src_r, c]))
            rx = x + (c * cell_w)
            ry = y + (r * cell_h)
            cmds.append(_rgb_cmd(rv, gv, bv))
            cmds.append(f"{_fmt(rx)} {_fmt(ry)} {_fmt(cell_w + 0.2)} {_fmt(cell_h + 0.2)} re f")


def _build_pdf_from_payload(test_dict):
    lines = _build_text_lines(test_dict)
    features = _extract_audio_visual_features(test_dict.get("audio_path"))

    cmds = []

    # Header text area
    y_start = 770
    line_height = 12.5
    for idx, line in enumerate(lines):
        y = y_start - (idx * line_height)
        if y < 435:
            break
        _append_text(cmds, 45, y, line, size=10, bold=(idx == 0))

    # Audio metadata row
    if features:
        _append_text(
            cmds,
            45,
            402,
            f"Audio Features: {features['sample_rate']} Hz, {features['duration']:.2f}s",
            size=9,
        )
    else:
        _append_text(cmds, 45, 402, "Audio Features: unavailable for this recording", size=9)

    # Waveform
    _append_text(cmds, 45, 376, "Waveform", size=10, bold=True)
    _append_panel(cmds, 45, 290, 522, 76, bg=(0.02, 0.05, 0.12), border=(0.80, 0.87, 0.98))
    _draw_axis_labels(cmds, 45, 290, 522, 76, "Time", "Amplitude")
    if features:
        _draw_waveform(cmds, features["waveform"], 50, 295, 512, 66)

    # Spectrogram
    _append_text(cmds, 45, 272, "Spectrogram", size=10, bold=True)
    _append_panel(cmds, 45, 173, 522, 88, bg=(0.02, 0.03, 0.09), border=(0.80, 0.87, 0.98))
    _draw_axis_labels(cmds, 45, 173, 522, 88, "Time", "Frequency")
    if features:
        _draw_heatmap(cmds, features["spectrogram"], 50, 178, 512, 78, flip_y=True)

    # MFCC
    _append_text(cmds, 45, 156, "MFCC (13 Coefficients)", size=10, bold=True)
    _append_panel(cmds, 45, 58, 522, 88, bg=(0.02, 0.03, 0.09), border=(0.80, 0.87, 0.98))
    _draw_axis_labels(cmds, 45, 58, 522, 88, "Time", "Coefficient")
    if features:
        _draw_heatmap(cmds, features["mfcc"], 50, 63, 512, 78, flip_y=False)

    if not features:
        _append_text(
            cmds,
            55,
            36,
            "Note: Could not decode the uploaded audio for feature visualization.",
            size=8,
        )

    content_stream = "\n".join(cmds).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>"
    )
    objects.append(
        b"<< /Length "
        + str(len(content_stream)).encode("ascii")
        + b" >>\nstream\n"
        + content_stream
        + b"\nendstream"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010} 00000 n \n".encode("ascii"))

    out.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(out)


def build_voice_report_pdf(test_dict):
    return _build_pdf_from_payload(test_dict)
