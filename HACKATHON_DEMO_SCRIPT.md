# NeuroGuard Demo Script (3 Minutes)

## 1. Problem (20 sec)
- Stress and neurological warning signs are often missed early.
- Counterfeit medicine risk also impacts patient safety.
- NeuroGuard addresses both with one practical platform.

## 2. User Flow (2 min)
1. Open home page and register a user.
2. Show OTP flow:
   - If SMTP configured: email OTP mode.
   - If not: safe demo fallback OTP mode.
3. Login and run voice test:
   - Upload sample audio.
   - Show stress level, score, detailed report.
   - Download PDF report.
4. Open Contact page:
   - Submit issue/escalation message.
5. Open Admin Insights Dashboard:
   - Show total tests, average stress, high-stress count, message inbox.

## 3. Technical Highlights (30 sec)
- Flask + JWT auth + secure middleware (headers, payload guard, rate-limit).
- ML-based voice feature extraction + classification.
- Structured detailed report generation + PDF export.
- Persistent storage for tests and contact messages.

## 4. Impact + Close (10 sec)
- Faster triage for mental/neurological risk screening.
- Better trust and traceability in medicine verification.
- Built as a scalable base for real healthcare workflows.
