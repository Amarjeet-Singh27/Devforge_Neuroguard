# NeuroGuard 10/10 Sprint

## Goal
Ship a stable, polished, demo-ready build with a live URL and a clean GitHub repo for hackathon judging.

## Phase 1: Critical Demo Reliability
- [x] Fix visible text/encoding issues on core demo page (`voice-test.html`)
- [x] Fix misleading microphone warning (show HTTPS/localhost requirement clearly)
- [ ] Verify fresh voice test flow end-to-end on deployed URL
- [ ] Verify PDF report downloads with graphs on deployed URL

## Phase 2: UX and Consistency
- [ ] Align header/footer/navigation consistency across all main pages
- [ ] Standardize success/error/loading messaging styles
- [ ] Verify mobile layout for index, dashboard, voice, medicine, contact

## Phase 3: Backend Hardening
- [ ] Add focused tests for report generation and voice upload edge cases
- [ ] Add runtime checks/logging for audio decode and FFmpeg fallback paths
- [ ] Validate all production env vars and fallback behavior

## Phase 4: Submission Pack
- [ ] Final README polish (problem, architecture, setup, deploy, demo flow)
- [ ] Add final screenshots/GIF and short demo notes
- [ ] Final smoke test checklist run before submission

## Today Progress
- Added deployment-ready runtime files/config (`wsgi.py`, `render.yaml`, `Procfile`, gunicorn dependency).
- Began polish sprint with reliability fixes on the voice page.
