## ML Pipeline Utilities

### Train model

```bash
python train_model.py
```

This trains a `RandomForestClassifier` from `dataset/low`, `dataset/medium`, `dataset/high` and saves `model.pkl`.

### Evaluate model

```bash
python evaluate_model.py
```

This loads `model.pkl`, evaluates on a train/test split of the dataset, prints:
- Accuracy
- Classification report
- Confusion matrix

It also saves metrics to `model_metrics.json`.

### Labeling API for dataset/unlabeled

List unlabeled files:

```http
GET /api/voice/dataset/unlabeled
Authorization: Bearer <jwt_token>
```

Label one file (moves it from `dataset/unlabeled` to `dataset/{label}`):

```http
POST /api/voice/dataset/label
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "file_name": "Recording.m4a",
  "label": "low"
}
```

Valid labels: `low`, `medium`, `high`.

# NeuroGuard API Documentation

## Overview
Complete REST API for voice health screening, prescription management, and medicine verification.

---

## 📋 Authentication Endpoints

### 1. Register User
**POST** `/api/auth/register`

**Request:**
```json
{
  "email": "patient@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "user_type": "patient",
  "age": 45
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "email": "patient@example.com",
    "full_name": "John Doe",
    "user_type": "patient",
    "created_at": "2024-01-20T10:30:00"
  },
  "access_token": "jwt_token_here"
}
```

---

### 2. Login
**POST** `/api/auth/login`

**Request:**
```json
{
  "email": "patient@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user": {...},
  "access_token": "jwt_token_here"
}
```

---

### 3. Get Profile
**GET** `/api/auth/profile`

**Headers:** `Authorization: Bearer {token}`

**Response:**
```json
{
  "id": "uuid",
  "email": "patient@example.com",
  "full_name": "John Doe",
  "user_type": "patient",
  "created_at": "2024-01-20T10:30:00"
}
```

---

### 4. Update Profile
**PUT** `/api/auth/update-profile`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "full_name": "John Updated",
  "age": 46,
  "medical_history": "Hypertension"
}
```

---

## 🎙️ Voice Analysis Endpoints

### 1. Upload & Analyze Voice
**POST** `/api/voice/test`

**Headers:** `Authorization: Bearer {token}`

**Request:** (Form Data)
- File: audio file (WAV, MP3, OGG, M4A, FLAC)

**Response:**
```json
{
  "message": "Voice test completed",
  "test_result": {
    "id": "uuid",
    "patient_id": "uuid",
    "risk_level": "Medium",
    "risk_score": 55.5,
    "slurring_score": 45.2,
    "speech_delay_score": 62.1,
    "frequency_variation_score": 48.3,
    "tremor_score": 61.2,
    "recommendations": "CAUTION: Some neurological indicators detected...",
    "test_date": "2024-01-20T10:35:00"
  }
}
```

---

### 2. Get Voice Test History
**GET** `/api/voice/history`

**Headers:** `Authorization: Bearer {token}`

**Response:**
```json
{
  "total_tests": 5,
  "tests": [
    {
      "id": "uuid",
      "risk_level": "Low",
      "risk_score": 25.5,
      "test_date": "2024-01-20T10:35:00"
    }
  ]
}
```

---

### 3. Get Specific Test Result
**GET** `/api/voice/test/{test_id}`

**Headers:** `Authorization: Bearer {token}`

---

### 4. Get Statistics
**GET** `/api/voice/stats`

**Headers:** `Authorization: Bearer {token}`

**Response:**
```json
{
  "total_tests": 5,
  "average_risk_score": 42.3,
  "risk_distribution": {
    "Low": 3,
    "Medium": 1,
    "High": 1
  },
  "latest_test": {...}
}
```

---

## 💊 Medicine Verification Endpoints

### 1. Register Medicine Batch
**POST** `/api/medicine/register-batch`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "batch_id": "BATCH-2024-001",
  "name": "Aspirin 500mg",
  "manufacturer": "Pharma Corp",
  "expiry_date": "2026-02-28"
}
```

**Response:**
```json
{
  "message": "Medicine batch registered successfully",
  "batch_id": "BATCH-2024-001",
  "root_hash": "sha256_hash_value",
  "qr_data": "BATCH:BATCH-2024-001|HASH:sha256_hash|VERIFY:verification_code"
}
```

---

### 2. Add Supply Chain Record
**POST** `/api/medicine/add-supply-chain`

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "batch_id": "BATCH-2024-001",
  "location": "Distribution Center A",
  "handler": "XYZ Distribution"
}
```

**Response:**
```json
{
  "message": "Supply chain record added",
  "previous_hash": "previous_hash_value",
  "current_hash": "new_hash_value",
  "location": "Distribution Center A",
  "handler": "XYZ Distribution"
}
```

---

### 3. Verify Medicine Authenticity
**GET** `/api/medicine/verify/{batch_id}`

**Response:**
```json
{
  "batch_id": "BATCH-2024-001",
  "medicine_name": "Aspirin 500mg",
  "manufacturer": "Pharma Corp",
  "is_authentic": true,
  "chain_valid": true,
  "supply_chain": [
    {
      "location": "Manufacturer",
      "handler": "Pharma Corp",
      "timestamp": "2024-01-15T08:00:00",
      "hash": "root_hash"
    },
    {
      "location": "Distribution Center A",
      "handler": "XYZ Distribution",
      "timestamp": "2024-01-16T10:30:00",
      "hash": "hash_2"
    }
  ],
  "verification_details": [...]
}
```

---

### 4. Generate QR Code
**GET** `/api/medicine/qr-generate/{batch_id}`

**Response:**
```json
{
  "batch_id": "BATCH-2024-001",
  "qr_data": "BATCH:BATCH-2024-001|HASH:...",
  "medicine_name": "Aspirin 500mg"
}
```

---

### 5. List Medicine Batches
**GET** `/api/medicine/list-batches?page=1&per_page=10`

**Headers:** `Authorization: Bearer {token}`

---

## 🔐 Health Check
**GET** `/api/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "NeuroGuard"
}
```

---

## Risk Levels

- **Low (0-33%):** Normal voice assessment
- **Medium (33-66%):** Caution - consult doctor within 1-2 weeks
- **High (66-100%):** Urgent - consult neurologist immediately

---

## Error Responses

```json
{
  "error": "Error message description"
}
```

**Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `409` - Conflict
- `500` - Internal Server Error
