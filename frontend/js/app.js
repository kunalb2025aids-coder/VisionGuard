// VisionGuard AI Frontend Application Logic
const API_BASE = ""; // Relative API base URL

let categoryChart = null;
let severityChart = null;
let trendChart = null;
let cameraStatusTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  if (window.vgWS) window.vgWS.init();
  if (window.initCopilot) window.initCopilot();
  initGlobalAssetSelector();
  initNavigation();
  checkHealth();
  loadDashboard();
  setupImageDetection();
  setupVideoAnalysis();
  setupMaintenanceModal();
  setupIndustrialCamera();
});

function initGlobalAssetSelector() {
  const assetSelect = document.getElementById("global-asset-select");
  if (assetSelect) {
    assetSelect.addEventListener("change", (e) => {
      const assetId = e.target.value;
      if (window.twin) window.twin.loadAsset(assetId);
      if (window.vgTelemetry) {
        window.vgTelemetry.currentAsset = assetId;
        window.vgTelemetry.fetchLatestTelemetry();
        window.vgTelemetry.fetchPredictionStatus();
      }
      if (window.vgCopilot) {
        window.vgCopilot.currentAsset = assetId;
      }
    });
  }

  const overlayBtn = document.getElementById("btn-twin-toggle-overlays");
  if (overlayBtn) {
    let overlaysOn = true;
    overlayBtn.addEventListener("click", () => {
      overlaysOn = !overlaysOn;
      window.twin?.toggleOverlays(overlaysOn);
      overlayBtn.innerHTML = overlaysOn
        ? `<i class="bi bi-bounding-box me-1"></i> Defect Overlays`
        : `<i class="bi bi-eye-slash me-1"></i> Overlays Off`;
    });
  }
}

// 1. Navigation SPA Controller
function initNavigation() {
  const navLinks = document.querySelectorAll(".nav-link-custom");
  navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const targetPage = link.getAttribute("data-page");
      if (!targetPage) return;

      navLinks.forEach((l) => l.classList.remove("active"));
      link.classList.add("active");

      document.querySelectorAll(".page-view").forEach((view) => {
        view.style.display = "none";
      });

      const activeView = document.getElementById(`page-${targetPage}`);
      if (activeView) {
        activeView.style.display = "block";
      }

      document.getElementById("current-page-title").textContent = link.textContent.trim();

      // Trigger page specific reloads
      if (targetPage === "dashboard") loadDashboard();
      if (targetPage === "digital-twin") {
        setTimeout(() => {
          window.initConveyorDigitalTwin("twin-canvas-container");
          window.twin?.onWindowResize();
        }, 50);
      }
      if (targetPage === "telemetry") {
        window.initTelemetryController();
      }
      if (targetPage === "camera") updateCameraStatus();
      if (targetPage === "history") loadDetectionHistory();
      if (targetPage === "maintenance") loadMaintenanceTasks();
      if (targetPage === "reports") loadReports();
    });
  });
}

// 2. Health & System Status Check
async function checkHealth() {
  const badge = document.getElementById("system-status-badge");
  const modelBanner = document.getElementById("model-alert-banner");

  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    if (data.status === "healthy") {
      badge.className = "status-badge online";
      badge.innerHTML = `<i class="bi bi-circle-fill" style="font-size: 0.5rem;"></i> System Online`;
    } else {
      badge.className = "status-badge offline";
      badge.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> DB Offline`;
    }

    if (!data.model_loaded) {
      if (modelBanner) {
        modelBanner.style.display = "flex";
        document.getElementById("model-alert-text").innerText =
          "Missing Trained Model Weights: 'models/best.pt' not found. Custom conveyor belt predictions require trained model weights. Run 'python train_yolo.py' or place your trained 'best.pt' file into the 'models/' directory.";
      }
    } else {
      if (modelBanner) modelBanner.style.display = "none";
    }
  } catch (err) {
    if (badge) {
      badge.className = "status-badge offline";
      badge.innerHTML = `<i class="bi bi-wifi-off"></i> Connection Error`;
    }
  }
}

// 3. Dashboard Data & Charts
async function loadDashboard() {
  try {
    const res = await fetch(`${API_BASE}/api/dashboard/summary`);
    if (!res.ok) throw new Error("Failed to load dashboard summary");
    const data = await res.json();

    // Update Widgets
    document.getElementById("stat-total-inspections").innerText = data.total_inspections;
    document.getElementById("stat-total-defects").innerText = data.total_defects;
    document.getElementById("stat-high-priority").innerText = data.high_priority_defects;
    document.getElementById("stat-completed-maintenance").innerText = data.completed_maintenance;

    // Render Charts
    renderCategoryChart(data.defects_by_category);
    renderSeverityChart(data.defects_by_severity);
    renderTrendChart(data.inspection_trends);

    // Render Recent History Table
    renderRecentHistoryTable(data.recent_inspections);
  } catch (err) {
    console.error("Dashboard error:", err);
  }
}

function renderCategoryChart(categoryData) {
  const ctx = document.getElementById("chart-defects-category");
  if (!ctx) return;

  const labels = Object.keys(categoryData);
  const values = Object.values(categoryData);

  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Defects Count",
          data: values,
          backgroundColor: ["#38bdf8", "#f59e0b", "#ef4444", "#fb923c", "#a855f7"],
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
        y: { ticks: { color: "#94a3b8", stepSize: 1 }, grid: { color: "#334155" } }
      }
    }
  });
}

function renderSeverityChart(severityData) {
  const ctx = document.getElementById("chart-defects-severity");
  if (!ctx) return;

  const labels = Object.keys(severityData);
  const values = Object.values(severityData);

  if (severityChart) severityChart.destroy();

  severityChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: ["#10b981", "#f59e0b", "#fb923c", "#ef4444"],
          borderWidth: 2,
          borderColor: "#1e293b"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: "#94a3b8" } }
      }
    }
  });
}

function renderTrendChart(trends) {
  const ctx = document.getElementById("chart-inspection-trends");
  if (!ctx) return;

  const labels = trends.map((t) => t.date);
  const inspections = trends.map((t) => t.inspections);
  const defects = trends.map((t) => t.defects);

  if (trendChart) trendChart.destroy();

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels.length ? labels : ["Today"],
      datasets: [
        {
          label: "Inspections",
          data: inspections.length ? inspections : [0],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.1)",
          fill: true,
          tension: 0.3
        },
        {
          label: "Defects",
          data: defects.length ? defects : [0],
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          fill: true,
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#94a3b8" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
        y: { ticks: { color: "#94a3b8", stepSize: 1 }, grid: { color: "#334155" } }
      }
    }
  });
}

function renderRecentHistoryTable(inspections) {
  const tbody = document.getElementById("recent-history-tbody");
  if (!tbody) return;

  if (!inspections || inspections.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No inspection history recorded yet. Upload an image or video to begin.</td></tr>`;
    return;
  }

  tbody.innerHTML = inspections
    .map((i) => {
      const dateStr = new Date(i.created_at).toLocaleString();
      const statusBadge =
        i.defects_count > 0
          ? `<span class="sev-badge high">${i.defects_count} Defects</span>`
          : `<span class="sev-badge low">Pass</span>`;

      return `
      <tr>
        <td>#${i.id}</td>
        <td><i class="bi ${i.media_type === "image" ? "bi-image" : "bi-camera-reels"} me-2 text-info"></i>${i.filename}</td>
        <td><span class="text-capitalize">${i.media_type}</span></td>
        <td>${statusBadge}</td>
        <td>${i.processing_time_ms} ms</td>
        <td>${dateStr}</td>
      </tr>
    `;
    })
    .join("");
}

// 4. Industrial Camera Controller (Real-time Stream & Manager/Supervisor Alerts)
function setupIndustrialCamera() {
  const btnStart = document.getElementById("btn-start-camera");
  const btnStop = document.getElementById("btn-stop-camera");
  const feedImg = document.getElementById("live-mjpeg-feed");
  const placeholder = document.getElementById("mjpeg-placeholder");

  if (!btnStart || !btnStop) return;

  btnStart.addEventListener("click", async () => {
    const source = document.getElementById("camera-source-input").value;
    const mgrEmail = document.getElementById("camera-manager-email").value;
    const supEmail = document.getElementById("camera-supervisor-email").value;

    btnStart.disabled = true;
    btnStart.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Connecting...`;

    try {
      const res = await fetch(`${API_BASE}/api/camera/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camera_source: source,
          manager_email: mgrEmail,
          supervisor_email: supEmail
        })
      });

      if (!res.ok) throw new Error("Failed to connect camera stream");

      feedImg.src = `${API_BASE}/api/camera/feed?t=${Date.now()}`;
      feedImg.style.display = "block";
      if (placeholder) placeholder.style.display = "none";

      btnStop.disabled = false;
      btnStart.innerHTML = `<i class="bi bi-record-circle me-1"></i> Camera Connected`;

      if (cameraStatusTimer) clearInterval(cameraStatusTimer);
      cameraStatusTimer = setInterval(updateCameraStatus, 2000);
      updateCameraStatus();
    } catch (err) {
      alert(`Camera connection error: ${err.message}`);
      btnStart.disabled = false;
      btnStart.innerHTML = `<i class="bi bi-record-circle me-1"></i> Start Camera Stream`;
    }
  });

  btnStop.addEventListener("click", async () => {
    btnStop.disabled = true;
    try {
      await fetch(`${API_BASE}/api/camera/stop`, { method: "POST" });
      feedImg.style.display = "none";
      feedImg.src = "";
      if (placeholder) placeholder.style.display = "block";

      btnStart.disabled = false;
      btnStart.innerHTML = `<i class="bi bi-record-circle me-1"></i> Start Camera Stream`;

      if (cameraStatusTimer) clearInterval(cameraStatusTimer);
      updateCameraStatus();
    } catch (err) {
      console.error(err);
    }
  });
}

async function updateCameraStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/camera/status`);
    if (!res.ok) return;
    const data = await res.json();

    const statusText = document.getElementById("cam-status-text");
    if (statusText) {
      statusText.innerText = data.is_running ? "LIVE MONITORING" : "Stopped";
      statusText.className = data.is_running ? "text-success fw-bold" : "text-secondary";
    }

    document.getElementById("cam-frames-text").innerText = data.frames_processed;
    document.getElementById("cam-defects-text").innerText = data.defects_detected_count;
    document.getElementById("cam-alerts-text").innerText = data.alerts_sent_count;
  } catch (err) {
    console.error("Camera status error:", err);
  }
}

// 5. Image Defect Detection Controller
function setupImageDetection() {
  const form = document.getElementById("image-upload-form");
  const fileInput = document.getElementById("image-file-input");
  const preview = document.getElementById("image-preview");
  const dropzone = document.getElementById("image-dropzone");

  if (!form || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        preview.src = e.target.result;
        preview.style.display = "block";
      };
      reader.readAsDataURL(file);
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      alert("Please select an image file first.");
      return;
    }

    const btn = document.getElementById("btn-analyze-image");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Analyzing Image with YOLOv11...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/detections/image`, {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        let msg = data.detail || "Image analysis failed";
        if (typeof data.detail === "object" && data.detail.message) {
          msg = `${data.detail.message}\n\nInstructions: ${data.detail.instructions}`;
        }
        alert(`Error: ${msg}`);
        return;
      }

      // Display Image Analysis Results
      document.getElementById("image-result-card").style.display = "block";
      document.getElementById("annotated-image-res").src = `${API_BASE}/${data.result_path}?t=${Date.now()}`;
      document.getElementById("res-processing-time").innerText = `${data.processing_time_ms} ms`;
      document.getElementById("res-defect-count").innerText = data.defects_count;
      document.getElementById("res-high-priority").innerText = data.high_priority_count;

      // Render Detection Breakdown List
      const listContainer = document.getElementById("res-detections-list");
      if (data.detections.length === 0) {
        listContainer.innerHTML = `<div class="alert alert-success mt-3"><i class="bi bi-check-circle-fill me-2"></i>No conveyor belt defects detected in this image.</div>`;
      } else {
        listContainer.innerHTML = data.detections
          .map(
            (d) => `
          <div class="d-flex align-items-center justify-content-between p-2 mb-2 rounded bg-dark border border-secondary">
            <div>
              <strong class="text-white">${d.defect_class}</strong>
              <div class="small text-muted">Confidence: ${(d.confidence * 100).toFixed(1)}%</div>
            </div>
            <div>
              <span class="sev-badge ${d.severity.toLowerCase()}">${d.severity}</span>
            </div>
          </div>
        `
          )
          .join("");
      }
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-cpu me-2"></i> Run AI Defect Detection`;
    }
  });
}

// 6. Video Analysis Controller
function setupVideoAnalysis() {
  const form = document.getElementById("video-upload-form");
  const fileInput = document.getElementById("video-file-input");

  if (!form || !fileInput) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      alert("Please select a video file.");
      return;
    }

    const btn = document.getElementById("btn-analyze-video");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Processing Video Frames...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/detections/video`, {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        let msg = data.detail || "Video analysis failed";
        if (typeof data.detail === "object" && data.detail.message) {
          msg = `${data.detail.message}\n\nInstructions: ${data.detail.instructions}`;
        }
        alert(`Error: ${msg}`);
        return;
      }

      // Display Video Result
      document.getElementById("video-result-card").style.display = "block";
      const videoPlayer = document.getElementById("annotated-video-res");
      videoPlayer.src = `${API_BASE}/${data.result_path}`;
      videoPlayer.load();

      document.getElementById("video-res-time").innerText = `${data.processing_time_ms} ms`;
      document.getElementById("video-res-defects").innerText = data.defects_count;
    } catch (err) {
      alert(`Video processing error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-film me-2"></i> Analyze Video Feed`;
    }
  });
}

// 7. Detection History Controller
async function loadDetectionHistory() {
  const tbody = document.getElementById("history-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/api/detections`);
    if (!res.ok) throw new Error("Failed to fetch detection history");
    const inspections = await res.json();

    if (inspections.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No inspection records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = inspections
      .map(
        (i) => `
      <tr>
        <td>#${i.id}</td>
        <td><strong>${i.filename}</strong></td>
        <td><span class="badge bg-secondary text-uppercase">${i.media_type}</span></td>
        <td><span class="sev-badge ${i.defects_count > 0 ? "high" : "low"}">${i.defects_count} Defects</span></td>
        <td>${i.processing_time_ms} ms</td>
        <td>${new Date(i.created_at).toLocaleString()}</td>
        <td>
          <div class="d-flex gap-1">
            <a href="${API_BASE}/${i.result_path}" target="_blank" class="btn btn-sm btn-outline-info">
              <i class="bi bi-eye me-1"></i> View Output
            </a>
            <button class="btn btn-sm btn-outline-danger" onclick="deleteInspectionRecord(${i.id})" title="Delete inspection record">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `
      )
      .join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-danger py-4">Failed to load history: ${err.message}</td></tr>`;
  }
}

async function deleteInspectionRecord(id) {
  if (!confirm(`Are you sure you want to delete Inspection record #${id}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/api/detections/${id}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Failed to delete inspection record");
    loadDetectionHistory();
    loadDashboard();
    if (window.vgWS) {
      window.vgWS.showToast("Record Deleted", `Inspection #${id} has been removed.`, "info");
    }
  } catch (err) {
    alert(`Delete failed: ${err.message}`);
  }
}

// 8. Maintenance Management Controller
async function loadMaintenanceTasks() {
  const tbody = document.getElementById("maintenance-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/api/maintenance`);
    if (!res.ok) throw new Error("Failed to load maintenance tasks");
    const tasks = await res.json();

    if (tasks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No active maintenance tasks. High-priority AI detections will trigger tasks automatically.</td></tr>`;
      return;
    }

    tbody.innerHTML = tasks
      .map(
        (t) => `
      <tr>
        <td>#${t.id}</td>
        <td><strong>${t.title}</strong><div class="small text-muted">${t.defect_class || "Conveyor Belt"}</div></td>
        <td><span class="sev-badge ${t.severity.toLowerCase()}">${t.severity}</span></td>
        <td><span class="status-pill ${t.status.toLowerCase().replace(" ", "-")}">${t.status}</span></td>
        <td><i class="bi bi-person me-1 text-muted"></i>${t.assigned_personnel || "Unassigned"}</td>
        <td>${t.due_date || "Not set"}</td>
        <td>
          <button class="btn btn-sm btn-outline-primary" onclick="openEditTaskModal(${t.id}, '${t.title.replace(/'/g, "\\'")}', '${t.status}', '${t.severity}', '${t.assigned_personnel || ""}', '${t.due_date || ""}', '${(t.notes || "").replace(/'/g, "\\'")}')">
            <i class="bi bi-pencil me-1"></i> Edit
          </button>
        </td>
      </tr>
    `
      )
      .join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-danger py-4">Error loading tasks: ${err.message}</td></tr>`;
  }
}

function setupMaintenanceModal() {
  const form = document.getElementById("edit-task-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const taskId = document.getElementById("edit-task-id").value;
    const payload = {
      title: document.getElementById("edit-task-title").value,
      status: document.getElementById("edit-task-status").value,
      severity: document.getElementById("edit-task-severity").value,
      assigned_personnel: document.getElementById("edit-task-assigned").value,
      due_date: document.getElementById("edit-task-duedate").value,
      notes: document.getElementById("edit-task-notes").value
    };

    try {
      const res = await fetch(`${API_BASE}/api/maintenance/${taskId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Failed to update task");

      const modalEl = document.getElementById("editTaskModal");
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      loadMaintenanceTasks();
      loadDashboard();
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    }
  });
}

function openEditTaskModal(id, title, status, severity, assigned, dueDate, notes) {
  document.getElementById("edit-task-id").value = id;
  document.getElementById("edit-task-title").value = title;
  document.getElementById("edit-task-status").value = status;
  document.getElementById("edit-task-severity").value = severity;
  document.getElementById("edit-task-assigned").value = assigned;
  document.getElementById("edit-task-duedate").value = dueDate;
  document.getElementById("edit-task-notes").value = notes;

  const modal = new bootstrap.Modal(document.getElementById("editTaskModal"));
  modal.show();
}

// 9. Reports & Analytics Controller
async function loadReports() {
  try {
    const res = await fetch(`${API_BASE}/api/reports/inspections`);
    if (!res.ok) throw new Error("Failed to load reports summary");
    const data = await res.json();

    document.getElementById("report-stat-total").innerText = data.summary.total_inspections;
    document.getElementById("report-stat-defects").innerText = data.summary.total_defects_found;
    document.getElementById("report-stat-high").innerText = data.summary.high_priority_defects;
    document.getElementById("report-stat-avg-time").innerText = `${data.summary.avg_processing_time_ms} ms`;
  } catch (err) {
    console.error("Reports error:", err);
  }
}
