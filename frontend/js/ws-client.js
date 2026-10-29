/**
 * VisionGuard AI 2.0 - WebSocket Client
 * Real-time event streaming, auto-reconnect, and UI notifications.
 */
class VisionGuardWebSocketClient {
  constructor() {
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 10000;
    this.baseDelay = 1000;
    this.listeners = new Map();
    this.isConnected = false;
    this.statusElement = null;
    this.toastContainer = null;
  }

  init() {
    this.statusElement = document.getElementById("ws-status-badge");
    this.toastContainer = document.getElementById("toast-container");
    this.connect();
  }

  getWebSocketUrl() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8000";
    return `${protocol}//${host}/ws/visionguard`;
  }

  connect() {
    const url = this.getWebSocketUrl();
    this.updateStatus("connecting", "WS Connecting...");

    try {
      this.socket = new WebSocket(url);
    } catch (err) {
      console.warn("[WS] Connection creation failed:", err);
      this.scheduleReconnect();
      return;
    }

    this.socket.onopen = () => {
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.updateStatus("online", "WS Live");
      console.log("[WS] Connected to VisionGuard event stream");
    };

    this.socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.dispatch(msg);
      } catch (err) {
        console.warn("[WS] Failed to parse message:", event.data, err);
      }
    };

    this.socket.onclose = (event) => {
      this.isConnected = false;
      this.updateStatus("offline", "WS Disconnected");
      console.log(`[WS] Disconnected (code: ${event.code}). Scheduling reconnect...`);
      this.scheduleReconnect();
    };

    this.socket.onerror = (err) => {
      console.warn("[WS] Error observed:", err);
      // onclose will follow and trigger reconnect
    };
  }

  scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(this.baseDelay * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.updateStatus("connecting", `Reconnecting (${Math.round(delay / 1000)}s)...`);
    setTimeout(() => {
      if (!this.isConnected) {
        this.connect();
      }
    }, delay);
  }

  updateStatus(state, text) {
    if (!this.statusElement) {
      this.statusElement = document.getElementById("ws-status-badge");
    }
    if (!this.statusElement) return;

    this.statusElement.className = `status-pill ${state}`;
    let icon = "bi-circle-fill";
    if (state === "connecting") icon = "bi-arrow-repeat spin";
    if (state === "offline") icon = "bi-wifi-off";

    this.statusElement.innerHTML = `<i class="bi ${icon}"></i> <span>${text}</span>`;
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  dispatch(event) {
    const eventType = event.event_type || event.type;
    const callbacks = this.listeners.get(eventType) || [];
    callbacks.forEach((cb) => {
      try {
        cb(event.payload || event);
      } catch (err) {
        console.error(`[WS] Error in listener for ${eventType}:`, err);
      }
    });

    // Also dispatch to wildcard listeners
    const wildcards = this.listeners.get("*") || [];
    wildcards.forEach((cb) => {
      try {
        cb(event);
      } catch (err) {
        console.error("[WS] Error in wildcard listener:", err);
      }
    });

    // Surface notifications for alerts and detections
    this.handleSystemNotification(eventType, event.payload || event);
  }

  handleSystemNotification(eventType, payload) {
    if (eventType === "alert.created") {
      this.showToast(
        "Industrial Alert",
        payload.title || "Critical conveyor condition detected",
        payload.severity === "Critical" ? "danger" : "warning"
      );
    } else if (eventType === "detection.created") {
      this.showToast(
        "Defect Detected",
        `${payload.defect_class || "Defect"} (${((payload.confidence || 0) * 100).toFixed(0)}% conf)`,
        payload.severity === "Critical" || payload.severity === "High" ? "danger" : "info"
      );
    } else if (eventType === "telemetry.anomaly") {
      this.showToast(
        "Telemetry Anomaly",
        `${payload.anomaly_type || "Anomaly"} detected on ${payload.asset_id || "conveyor"}`,
        "warning"
      );
    }
  }

  showToast(title, message, variant = "info") {
    if (!this.toastContainer) {
      this.toastContainer = document.getElementById("toast-container");
    }
    if (!this.toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `vg-toast vg-toast-${variant} animate-fade-in`;
    toast.innerHTML = `
      <div class="vg-toast-header">
        <strong class="me-auto"><i class="bi bi-bell-fill me-1"></i>${title}</strong>
        <small class="text-muted">${new Date().toLocaleTimeString()}</small>
        <button type="button" class="btn-close btn-close-white ms-2" onclick="this.parentElement.parentElement.remove()"></button>
      </div>
      <div class="vg-toast-body">${message}</div>
    `;

    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => toast.remove(), 400);
    }, 5000);
  }
}

// Global singleton instance
window.vgWS = new VisionGuardWebSocketClient();
