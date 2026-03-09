# NeuroGuard

NeuroGuard is a Flask-based healthcare demo platform that combines:
- Voice-based neurological risk screening
- JWT-authenticated user workflows
- Medicine batch authenticity verification using a hash-chain
- Contact/support message management
- PDF report generation for voice test results

## Tech Stack
- Python + Flask
- SQLite + SQLAlchemy
- JWT auth (`Flask-JWT-Extended`)
- Audio processing: `librosa`, `pydub`, FFmpeg
- ML model: `scikit-learn` (RandomForest)

## Project Structure
```text
project1/
  app.py                    # Flask app entry point
  config.py                 # App and environment configuration
  models.py                 # SQLAlchemy models
  model.py                  # Loads model.pkl and predicts labels
  train_model.py            # Train RandomForest model from dataset/
  evaluate_model.py         # Evaluate model and write model_metrics.json
  prepare_dataset.py        # Build dataset folders from uploads/root audio
  routes/
    auth.py
    voice.py
    medicine.py
    contact.py
  utils/
    voice_analyzer.py
    hash_chain.py
    pdf_report.py
  templates/                # Frontend pages
  static/                   # CSS/JS
  dataset/
    low/ medium/ high/ unlabeled/
  tests/
```

## Features
- User registration/login/profile with JWT tokens
- Optional OTP verification flow during signup (SMTP + fallback mode)
- Voice file upload and risk/stress analysis (`Low`, `Medium`, `High`)
- Voice test history + stats + downloadable PDF report
- Dataset labeling endpoints for moving files from `dataset/unlabeled` to labeled folders
- Medicine batch registration + supply-chain tracking + authenticity verification
- Contact form save/list endpoints
- Security headers + optional request size/rate-limit guards

## Requirements
- Python 3.10+
- FFmpeg available in system `PATH` (recommended for broader audio format support)

Install dependencies:
```bash
pip install -r requirements.txt
```

If you want HTTPS ad-hoc certificates in development:
```bash
pip install cryptography
```

## Environment Variables
Create a `.env` file in project root (optional for local dev, recommended for stable setup).

```env
# Core
JWT_SECRET_KEY=change-this-to-a-long-random-secret-at-least-32-chars
HOST=0.0.0.0
PORT=5001
USE_HTTPS=1
FLASK_DEBUG=0

# OTP / SMTP
OTP_EXPIRY_MINUTES=10
OTP_VERIFICATION_TOKEN_EXPIRY_MINUTES=20
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=1
ALLOW_OTP_FALLBACK=1

# Optional request guards
ENABLE_REQUEST_GUARDS=0
JSON_MAX_BYTES=262144
FORM_MAX_BYTES=10485760
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_REQUESTS=20
```

## Run the App
```bash
python app.py
```

Default behavior:
- Starts on `https://0.0.0.0:5001` when `USE_HTTPS=1`.
- If `cryptography` is not installed, app automatically falls back to HTTP and prints a warning.

Useful overrides:
```bash
# Force HTTP
set USE_HTTPS=0
python app.py
```

## Deploy (Recommended: Render)
This repo is now deployment-ready for Flask hosting with:
- `wsgi.py` (Gunicorn entrypoint)
- `render.yaml` (Blueprint config)
- Persistent storage path support for DB and uploads

### Render steps
1. Push your code to GitHub.
2. In Render, create a **Blueprint** and select your repo.
3. Render will use `render.yaml` to provision:
   - A Python web service
   - A persistent disk mounted at `/var/data`
4. Deploy and open:
   - `https://<your-render-domain>/voice-test.html`

### Production runtime
```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 180
```

### Key env vars used in deploy
- `APP_CONFIG=production`
- `DATABASE_URL=sqlite:////var/data/neuroguard.db`
- `UPLOAD_FOLDER=/var/data/uploads`
- `JWT_SECRET_KEY=<secure random secret>`

### Vercel note
Browser microphone capture works over HTTPS, but this backend architecture (Flask + persistent uploads + local DB/audio processing) is better hosted on Render/Railway/Fly/VM than plain Vercel serverless.

## Model Training Workflow
1. Prepare dataset folders and copy available audio:
```bash
python prepare_dataset.py
```

2. Ensure labeled samples exist in:
- `dataset/low`
- `dataset/medium`
- `dataset/high`

3. Train model:
```bash
python train_model.py
```
This writes `model.pkl`.

4. Evaluate model:
```bash
python evaluate_model.py
```
This writes `model_metrics.json`.

## Main API Endpoints
### Health
- `GET /api/health`

### Auth
- `GET /api/auth/otp-status`
- `POST /api/auth/request-otp`
- `POST /api/auth/verify-otp`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/profile` (JWT)
- `PUT /api/auth/update-profile` (JWT)
- `POST /api/auth/test-smtp` (debug/testing only)

### Voice
- `POST /api/voice/test` (JWT, multipart `audio`)
- `GET /api/voice/history` (JWT)
- `GET /api/voice/test/<test_id>` (JWT)
- `GET /api/voice/test/<test_id>/report.pdf` (JWT)
- `GET /api/voice/stats` (JWT)
- `GET /api/voice/model-metrics` (JWT)
- `GET /api/voice/dataset/unlabeled` (JWT)
- `POST /api/voice/dataset/label` (JWT)

### Medicine
- `POST /api/medicine/register-batch` (JWT)
- `POST /api/medicine/add-supply-chain` (JWT)
- `GET /api/medicine/verify/<batch_id>`
- `GET /api/medicine/list-batches` (JWT)
- `GET /api/medicine/qr-generate/<batch_id>`



## Testing
Run tests:
```bash
python -m pytest -q tests
```

If `pytest` is missing:
```bash
pip install pytest
```

## Notes
- Database is SQLite (`instance/neuroguard.db` in development).
- Uploaded audio files are stored in `uploads/`.
- This project is a screening/demo system and not a clinical diagnostic tool.

## Additional Docs
- `API_DOCUMENTATION.md`
- `HACKATHON_ARCHITECTURE.md`
- `HACKATHON_DEMO_SCRIPT.md`
- `HACKATHON_FINAL_CHECKLIST.md`
