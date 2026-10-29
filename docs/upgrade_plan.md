# VisionGuard AI 2.0 - Upgrade Plan
Generated: 2026-10-29

## Phase 0: Repository Audit

### Current Architecture
- FastAPI 0.110+ backend, Uvicorn
- SQLAlchemy 2.0, SQLite/PostgreSQL
- Pydantic v2 schemas
- YOLO11 + OpenCV inference
- Bootstrap 5 + Chart.js frontend (SPA)
- 7 routers: health, dashboard, detections, maintenance, alerts, reports, camera

### Existing Tables
- inspections, detections, maintenance_tasks, alerts, settings

### Existing API Routes
- GET /api/health
- GET /api/dashboard/summary
- POST /api/detections/image
- POST /api/detections/video
- GET /api/detections, GET /api/detections/{id}
- GET/POST/PUT /api/maintenance
- GET /api/alerts, PUT /api/alerts/{id}/read
- GET /api/reports/inspections, GET /api/reports/export
- POST /api/camera/start|stop, GET /api/camera/status|feed

### Bug Found
- alert_service.py line 54: server.as_string() should be msg.as_string()

### New Tables to Add (additive only)
- assets, components, telemetry_readings, anomaly_predictions, copilot_sessions

### Files to Modify
- backend/app/main.py - add new routers + WebSocket
- backend/app/models/entities.py - add new tables  
- backend/app/schemas/schemas.py - add new schemas
- backend/app/routers/__init__.py - import new routers
- backend/app/services/alert_service.py - fix bug
- frontend/index.html - full premium redesign
- frontend/css/style.css - premium design system
- frontend/js/app.js - modular SPA logic
- requirements.txt - add websockets, scikit-learn

### Files to Create
- backend/app/routers/assets.py
- backend/app/routers/telemetry.py
- backend/app/routers/predictions.py
- backend/app/routers/copilot.py
- backend/app/routers/ws.py
- backend/app/services/telemetry_service.py
- backend/app/services/prediction_service.py
- backend/app/services/copilot_service.py
- backend/app/services/event_bus.py
- frontend/js/digital-twin.js
- frontend/js/telemetry.js
- frontend/js/copilot.js
- frontend/js/ws-client.js
- tests/test_assets.py, test_telemetry.py, test_predictions.py, test_copilot.py
- docs/architecture_v2.md, docs/demo_guide.md
