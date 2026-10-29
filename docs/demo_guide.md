# VisionGuard AI 2.0 — Demonstration & Operator Guide

## 1. Quick Startup Instructions (Windows PowerShell)

Open PowerShell in the project root directory (`d:\data science project`):

```powershell
# 1. (Optional) Activate Virtual Environment if configured
# .\venv\Scripts\Activate.ps1

# 2. Verify dependencies are installed
pip install -r requirements.txt

# 3. Launch VisionGuard AI 2.0 ASGI Server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser to:
**[http://localhost:8000](http://localhost:8000)**

API Documentation (Swagger UI):
**[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 2. Step-by-Step Demonstration Walkthrough

### Step 1: Industrial Dashboard & Real-Time Status
1. Navigate to `http://localhost:8000`.
2. Notice the **futuristic graphite & cyber-cyan theme**, dynamic KPI statistics, and real-time Chart.js distribution charts.
3. Observe the header bar:
   - **Asset Selector**: Defaults to `CONV-01 (Line 1)`.
   - **WS Live Indicator**: Pulsing green badge confirms WebSocket connection to `/ws/visionguard`.
   - **System Health**: Green badge indicating database connection and model readiness state.

---

### Step 2: Interactive 3D Digital Twin (`3D Digital Twin` tab)
1. Click **3D Digital Twin** in the sidebar.
2. An interactive WebGL model of Conveyor Line 01 renders in the viewport:
   - **Motion**: The conveyor belt rubber surface animatedly scrolls based on simulated belt speed.
   - **Camera Controls**: Left-click and drag to **Orbit/Rotate**, right-click and drag to **Pan**, scroll to **Zoom**.
   - **Reset View**: Click the **Reset View** overlay button to smoothly return to the default isometric view.
3. **Raycast Component Selection**:
   - Hover your mouse over the **Head Roller**, **Tail Roller**, **Carry Idlers**, or **Drive Motor**. The cursor changes to a pointer.
   - Click on the **Primary Electric Drive Motor**. The camera focuses on the motor assembly, and the right-hand **Diagnostic Panel** updates with:
     - Component Health Score (e.g. 88% Health)
     - Operating State & Vibration RMS
     - Direct action buttons: **Ask AI Copilot** and **Schedule Maint**.
4. **Defect Overlays**:
   - Click **Defect Overlays** in the top-left toolbar to toggle glowing 3D beacon markers representing real cracks, edge tears, and misalignment locations on the belt.
5. **Asset Switching**:
   - Change the asset in the top bar to `CONV-02` or `CONV-03`. Notice the twin dynamically loads the specific asset's component inventory and health score.

---

### Step 3: Software-Only Sensor Simulator (`Telemetry & Simulator` tab)
1. Click **Telemetry & Simulator** in the sidebar.
2. Note the banner: `[Software-Only Deterministic Sensor Simulator Active - Zero external hardware required]`.
3. **Live Sensor Gauges**:
   - Review live cards for **Vibration RMS**, **Motor Temp**, **Motor Current**, **Belt Speed**, and **Bearing Temp**.
4. **Scenario Injection**:
   - In the dropdown, select **Gradual Vibration Increase (Bearing Wear)** and click **Inject Scenario**.
   - Watch the live line chart update as vibration rises towards the 4.5 mm/s warning threshold.
   - The vibration card badge flips from green `NORMAL` to pulsing red `ALERT`.
   - Connected WebSocket clients immediately display a real-time floating toast alert.
5. **Simulation Controls**:
   - Click **Pause** to freeze the stream.
   - Click **Step Clock** to advance single simulation frames manually.
   - Click **Reset Baseline** to return all sensors to normal operating baseline.

---

### Step 4: Explainable Anomaly Detection & Predictions
1. In the **Explainable Anomaly Indicators** card:
   - When vibration or temperature exceeds tolerances, explainable rules are displayed (e.g., `ISO 10816-3 Class II Limit Exceeded: Vibration 5.4 mm/s > 4.5 mm/s`).
   - The indicator shows the exact threshold breached, severity, and suggested inspection actions.
   - Note the clear distinction: **Visual Defect Detection (YOLO)** vs **Sensor Anomaly Detection (Threshold / IsolationForest)**.

---

### Step 5: Evidence-Grounded AI Maintenance Copilot
1. Click the **AI Copilot** button in the top header.
2. The sleek cyber drawer slides open from the right.
3. Click any of the pre-configured prompt chips:
   - *"Which conveyor needs inspection first?"*
   - *"Summarize the latest inspection."*
   - *"Show recent cracks on CONV-01."*
   - *"Which maintenance tasks are overdue?"*
   - *"Draft a maintenance work order."*
4. Observe the response:
   - Formatted in clean Markdown with bold bullet points.
   - **Grounded Evidence Badges**: Shows clickable reference pills citing actual database inspection IDs, detection records, or telemetry values.
   - **Engine Pill**: Indicates `Grounded Engine` (deterministic local retrieval) or optional cloud LLM if configured.
   - **Zero Hallucination**: The copilot never claims to see defects that do not exist in the database.

---

### Step 6: Computer Vision Defect Detection (Image & Video)
1. **Image Detection**:
   - Click **Image Detection** in the sidebar.
   - Drag and drop any conveyor belt image or click to select a test image.
   - Click **Run AI Defect Detection**.
   - If model weights `models/best.pt` are present, actual YOLOv11 bounding boxes and confidence scores render on the image.
   - If weights are missing, a friendly notification banner explains how to train or upload weights (`python train_yolo.py`) without crashing.
2. **Video Analysis**:
   - Upload an MP4 inspection video. The backend processes frame batches and returns an annotated video stream.

---

### Step 7: Maintenance Work Orders & CSV Reports
1. **Maintenance Tasks**:
   - Click **Maintenance** in the sidebar.
   - High and Critical priority detections automatically generate preliminary tasks.
   - Click **Edit** on any task to assign technicians, update due dates, modify severity, or change status (`In Progress`, `Completed`).
   - Saving immediately broadcasts `maintenance.updated` over WebSockets.
2. **Reports & Analytics**:
   - Click **Reports & Analytics** in the sidebar.
   - View inspection statistics and click **Export Detailed CSV Report** to download an audit file.
