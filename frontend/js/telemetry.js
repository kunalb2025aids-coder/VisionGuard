/**
 * VisionGuard AI 2.0 - Telemetry & Sensor Simulation Controller
 * Manages software-only deterministic sensor telemetry, scenario injections,
 * live Chart.js sensor gauges, and explainable anomaly prediction views.
 */

class TelemetryController {
  constructor() {
    this.currentAsset = "CONV-01";
    this.currentScenario = "normal";
    this.isPaused = false;
    this.simulationTimer = null;
    this.stepIndex = 0;
    this.telemetryChart = null;

    // Buffer for 30 historical points per channel
    this.history = {
      timestamps: [],
      temperature: [],
      vibration: [],
      current: [],
      speed: [],
      bearing_temp: []
    };
  }

  init() {
    this.setupChart();
    this.bindControls();
    this.fetchScenarios();
    this.fetchLatestTelemetry();
    this.fetchPredictionStatus();
    this.startAutoPolling();

    // Listen to real-time telemetry if WS is connected
    if (window.vgWS) {
      window.vgWS.on("telemetry.step", (data) => this.handleIncomingReadings(data.readings));
    }
  }

  setupChart() {
    const ctx = document.getElementById("telemetry-chart");
    if (!ctx || typeof Chart === "undefined") return;

    this.telemetryChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Vibration RMS (mm/s)",
            borderColor: "#00f2fe",
            backgroundColor: "rgba(0, 242, 254, 0.1)",
            borderWidth: 2,
            data: [],
            yAxisID: "y1",
            tension: 0.3
          },
          {
            label: "Motor Temp (°C)",
            borderColor: "#f59e0b",
            backgroundColor: "rgba(245, 158, 11, 0.1)",
            borderWidth: 2,
            data: [],
            yAxisID: "y2",
            tension: 0.3
          },
          {
            label: "Motor Current (A)",
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            borderWidth: 2,
            data: [],
            yAxisID: "y2",
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#94a3b8", maxTicksLimit: 8 }
          },
          y1: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Vibration (mm/s)", color: "#00f2fe" },
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#00f2fe" },
            min: 0,
            max: 12
          },
          y2: {
            type: "linear",
            position: "right",
            title: { display: true, text: "Temp (°C) / Current (A)", color: "#f59e0b" },
            grid: { drawOnChartArea: false },
            ticks: { color: "#f59e0b" },
            min: 20,
            max: 110
          }
        },
        plugins: {
          legend: { labels: { color: "#f8fafc", boxWidth: 12 } }
        }
      }
    });
  }

  bindControls() {
    // Scenario selector
    const scenarioSelect = document.getElementById("sim-scenario-select");
    if (scenarioSelect) {
      scenarioSelect.addEventListener("change", (e) => {
        this.currentScenario = e.target.value;
      });
    }

    // Trigger Scenario Button
    const btnTrigger = document.getElementById("btn-sim-trigger");
    if (btnTrigger) {
      btnTrigger.addEventListener("click", () => this.triggerScenario());
    }

    // Step Simulation Button
    const btnStep = document.getElementById("btn-sim-step");
    if (btnStep) {
      btnStep.addEventListener("click", () => this.stepSimulation());
    }

    // Pause/Resume Button
    const btnPause = document.getElementById("btn-sim-pause");
    if (btnPause) {
      btnPause.addEventListener("click", () => this.togglePause());
    }

    // Reset Scenario Button
    const btnReset = document.getElementById("btn-sim-reset");
    if (btnReset) {
      btnReset.addEventListener("click", () => this.resetSimulation());
    }
  }

  async fetchScenarios() {
    try {
      const res = await fetch("/api/telemetry/scenarios");
      if (!res.ok) return;
      const data = await res.json();
      const select = document.getElementById("sim-scenario-select");
      if (select && data.scenarios) {
        select.innerHTML = data.scenarios
          .map((s) => `<option value="${s.id}">${s.name} (${s.severity})</option>`)
          .join("");
      }
    } catch (err) {
      console.warn("Failed to fetch scenarios:", err);
    }
  }

  async triggerScenario() {
    const scenario = document.getElementById("sim-scenario-select")?.value || "normal";
    try {
      const res = await fetch(`/api/demo/scenarios/${scenario}?asset_id=${this.currentAsset}`, {
        method: "POST"
      });
      const data = await res.json();
      if (window.vgWS) {
        window.vgWS.showToast("Scenario Injected", `Injected "${data.scenario}" scenario into ${this.currentAsset}`, "info");
      }
      this.stepSimulation();
      this.fetchPredictionStatus();
    } catch (err) {
      console.error("Scenario trigger failed:", err);
    }
  }

  async stepSimulation() {
    try {
      const res = await fetch("/api/telemetry/simulate/step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_id: this.currentAsset,
          scenario: this.currentScenario,
          step_index: this.stepIndex++
        })
      });
      if (!res.ok) return;
      const data = await res.json();
      this.handleIncomingReadings(data.readings);
    } catch (err) {
      console.warn("Step simulation error:", err);
    }
  }

  togglePause() {
    this.isPaused = !this.isPaused;
    const btn = document.getElementById("btn-sim-pause");
    if (btn) {
      btn.innerHTML = this.isPaused
        ? `<i class="bi bi-play-fill me-1"></i> Resume`
        : `<i class="bi bi-pause-fill me-1"></i> Pause`;
      btn.className = this.isPaused ? "btn btn-sm btn-outline-success" : "btn btn-sm btn-outline-warning";
    }
  }

  async resetSimulation() {
    this.currentScenario = "normal";
    const select = document.getElementById("sim-scenario-select");
    if (select) select.value = "normal";
    this.stepIndex = 0;
    await this.stepSimulation();
    if (window.vgWS) {
      window.vgWS.showToast("Simulation Reset", "Reset conveyor telemetry to normal baseline.", "info");
    }
    this.fetchPredictionStatus();
  }

  async fetchLatestTelemetry() {
    try {
      const res = await fetch(`/api/telemetry/latest?asset_id=${this.currentAsset}`);
      if (!res.ok) return;
      const data = await res.json();
      this.handleIncomingReadings(data.readings);
    } catch (err) {
      console.warn("Error fetching telemetry:", err);
    }
  }

  handleIncomingReadings(readings) {
    if (!readings) return;
    const now = new Date().toLocaleTimeString();

    let vibVal = null, tempVal = null, currVal = null, spdVal = null, bTempVal = null;

    readings.forEach((r) => {
      const elVal = document.getElementById(`metric-val-${r.channel}`);
      if (elVal) {
        elVal.innerText = `${r.value.toFixed(1)} ${r.unit}`;
      }

      // Check anomaly badges
      const statusPill = document.getElementById(`metric-status-${r.channel}`);
      if (statusPill) {
        let isAbnormal = false;
        if (r.channel === "vibration" && r.value > 4.5) isAbnormal = true;
        if (r.channel === "temperature" && r.value > 75.0) isAbnormal = true;
        if (r.channel === "motor_current" && r.value > 45.0) isAbnormal = true;

        statusPill.innerText = isAbnormal ? "ALERT" : "NORMAL";
        statusPill.className = `metric-pill ${isAbnormal ? "pill-danger" : "pill-normal"}`;
      }

      if (r.channel === "vibration") vibVal = r.value;
      if (r.channel === "temperature") tempVal = r.value;
      if (r.channel === "motor_current") currVal = r.value;
      if (r.channel === "belt_speed") spdVal = r.value;
      if (r.channel === "bearing_temp") bTempVal = r.value;
    });

    // Push to chart
    if (this.telemetryChart && vibVal !== null) {
      const chartLabels = this.telemetryChart.data.labels;
      chartLabels.push(now);
      this.telemetryChart.data.datasets[0].data.push(vibVal);
      this.telemetryChart.data.datasets[1].data.push(tempVal || 45);
      this.telemetryChart.data.datasets[2].data.push(currVal || 28);

      if (chartLabels.length > 20) {
        chartLabels.shift();
        this.telemetryChart.data.datasets.forEach((ds) => ds.data.shift());
      }
      this.telemetryChart.update("none");
    }
  }

  async fetchPredictionStatus() {
    try {
      const res = await fetch(`/api/predictions/status?asset_id=${this.currentAsset}`);
      if (!res.ok) return;
      const data = await res.json();

      const badge = document.getElementById("pred-engine-badge");
      if (badge) {
        badge.innerText = data.engine_type || "Rule-Based + ML Ready";
      }

      // Populate explainable indicators list
      const container = document.getElementById("pred-anomalies-list");
      if (container && data.current_indicators) {
        if (data.current_indicators.length === 0) {
          container.innerHTML = `
            <div class="p-3 text-center text-muted small">
              <i class="bi bi-check-circle-fill text-success me-1"></i>
              No active sensor anomalies detected. Conveyor running within operational tolerances.
            </div>`;
        } else {
          container.innerHTML = data.current_indicators
            .map(
              (ind) => `
              <div class="card-custom mb-2 p-3 border border-${ind.severity === "Critical" ? "danger" : "warning"}">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <strong class="text-${ind.severity === "Critical" ? "danger" : "warning"}">
                    <i class="bi bi-exclamation-triangle-fill me-1"></i>${ind.type}
                  </strong>
                  <span class="badge ${ind.severity === "Critical" ? "bg-danger" : "bg-warning"}">${ind.severity}</span>
                </div>
                <div class="small text-muted mb-2">${ind.rule}</div>
                <div class="d-flex justify-content-between small">
                  <span>Current: <strong class="text-white">${ind.current_value}</strong></span>
                  <span>Threshold: <strong class="text-white">${ind.threshold}</strong></span>
                </div>
              </div>`
            )
            .join("");
        }
      }
    } catch (err) {
      console.warn("Prediction status error:", err);
    }
  }

  startAutoPolling() {
    this.simulationTimer = setInterval(() => {
      if (!this.isPaused) {
        this.stepSimulation();
      }
    }, 3000);
  }
}

// Global initialization helper
window.initTelemetryController = function () {
  if (!window.vgTelemetry) {
    window.vgTelemetry = new TelemetryController();
    window.vgTelemetry.init();
  }
  return window.vgTelemetry;
};
