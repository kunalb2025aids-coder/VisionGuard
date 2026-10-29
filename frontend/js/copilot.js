/**
 * VisionGuard AI 2.0 - AI Maintenance Copilot Assistant
 * Grounded conversational assistant with real evidence citations from database.
 */

class VisionGuardCopilot {
  constructor() {
    this.sessionId = "session_" + Math.random().toString(36).substring(2, 9);
    this.currentAsset = "CONV-01";
    this.messages = [];
    this.isQuerying = false;
  }

  init() {
    this.bindEvents();
    this.renderInitialMessage();
  }

  bindEvents() {
    const input = document.getElementById("copilot-input");
    const sendBtn = document.getElementById("btn-copilot-send");

    if (sendBtn && input) {
      sendBtn.addEventListener("click", () => this.handleSend());
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.handleSend();
        }
      });
    }

    // Toggle drawer
    const toggleBtn = document.getElementById("btn-toggle-copilot");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggleDrawer());
    }

    const closeBtn = document.getElementById("btn-close-copilot");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.closeDrawer());
    }
  }

  toggleDrawer() {
    const drawer = document.getElementById("copilot-drawer");
    if (drawer) {
      drawer.classList.toggle("open");
      if (drawer.classList.contains("open")) {
        document.getElementById("copilot-input")?.focus();
      }
    }
  }

  openWithPrompt(promptText) {
    const drawer = document.getElementById("copilot-drawer");
    if (drawer) {
      drawer.classList.add("open");
    }
    const input = document.getElementById("copilot-input");
    if (input) {
      input.value = promptText;
      this.handleSend();
    }
  }

  closeDrawer() {
    const drawer = document.getElementById("copilot-drawer");
    if (drawer) drawer.classList.remove("open");
  }

  renderInitialMessage() {
    const container = document.getElementById("copilot-messages");
    if (!container) return;

    container.innerHTML = `
      <div class="copilot-msg copilot-assistant animate-fade-in">
        <div class="msg-avatar"><i class="bi bi-robot"></i></div>
        <div class="msg-content">
          <div class="msg-header">
            <strong>VisionGuard AI Copilot</strong>
            <span class="badge bg-info text-dark">Grounded Engine</span>
          </div>
          <div class="msg-body">
            Hello! I am your AI Conveyor Reliability Assistant. I can analyze actual inspection records, telemetry sensor feeds, active work orders, and failure predictions.
            <div class="quick-chips mt-3">
              <span class="chip" onclick="window.vgCopilot.askPredefined('Which conveyor needs inspection first?')">Which conveyor needs inspection first?</span>
              <span class="chip" onclick="window.vgCopilot.askPredefined('Summarize the latest inspection.')">Summarize latest inspection</span>
              <span class="chip" onclick="window.vgCopilot.askPredefined('Show recent cracks on CONV-01.')">Show cracks on CONV-01</span>
              <span class="chip" onclick="window.vgCopilot.askPredefined('Which maintenance tasks are overdue?')">Overdue maintenance tasks</span>
              <span class="chip" onclick="window.vgCopilot.askPredefined('Draft a maintenance work order.')">Draft work order</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  askPredefined(question) {
    const input = document.getElementById("copilot-input");
    if (input) input.value = question;
    this.handleSend();
  }

  async handleSend() {
    const input = document.getElementById("copilot-input");
    if (!input) return;
    const question = input.value.trim();
    if (!question || this.isQuerying) return;

    input.value = "";
    this.appendUserMessage(question);
    this.showTypingIndicator();
    this.isQuerying = true;

    try {
      const res = await fetch("/api/copilot/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question,
          asset_id: this.currentAsset,
          session_id: this.sessionId
        })
      });

      this.removeTypingIndicator();

      if (!res.ok) {
        throw new Error(`Copilot service error (${res.status})`);
      }

      const data = await res.json();
      this.appendAssistantMessage(data.answer, data.evidence, data.llm_source);
    } catch (err) {
      this.removeTypingIndicator();
      this.appendAssistantMessage(
        `Apologies, I encountered an issue querying plant records: ${err.message}. Please verify the backend service is running.`,
        [],
        "Error"
      );
    } finally {
      this.isQuerying = false;
    }
  }

  appendUserMessage(text) {
    const container = document.getElementById("copilot-messages");
    if (!container) return;

    const el = document.createElement("div");
    el.className = "copilot-msg copilot-user animate-fade-in";
    el.innerHTML = `
      <div class="msg-content">
        <div class="msg-body">${this.escapeHtml(text)}</div>
      </div>
      <div class="msg-avatar"><i class="bi bi-person-fill"></i></div>
    `;
    container.appendChild(el);
    this.scrollToBottom();
  }

  appendAssistantMessage(text, evidence = [], llmSource = "Grounded") {
    const container = document.getElementById("copilot-messages");
    if (!container) return;

    const el = document.createElement("div");
    el.className = "copilot-msg copilot-assistant animate-fade-in";

    // Format markdown-style bold and bullets
    let formattedText = this.formatMarkdown(text);

    // Build evidence chips
    let evidenceHtml = "";
    if (evidence && evidence.length > 0) {
      evidenceHtml = `
        <div class="evidence-block mt-3 pt-2 border-top border-secondary">
          <div class="small text-muted mb-1"><i class="bi bi-shield-check me-1 text-cyan"></i>Verified Grounded Evidence (${evidence.length} sources):</div>
          <div class="evidence-pills">
            ${evidence
              .map(
                (ev) => `
              <span class="evidence-pill" title="${this.escapeHtml(JSON.stringify(ev.summary || ev))}">
                <i class="bi bi-file-earmark-text me-1"></i>${ev.type.toUpperCase()}: ${ev.title || ev.summary || "Record"}
              </span>`
              )
              .join("")}
          </div>
        </div>
      `;
    }

    el.innerHTML = `
      <div class="msg-avatar"><i class="bi bi-robot"></i></div>
      <div class="msg-content">
        <div class="msg-header">
          <strong>VisionGuard Copilot</strong>
          <span class="badge ${llmSource.includes("OpenAI") || llmSource.includes("Claude") ? "bg-primary" : "bg-info text-dark"}">${llmSource}</span>
        </div>
        <div class="msg-body">${formattedText}</div>
        ${evidenceHtml}
      </div>
    `;

    container.appendChild(el);
    this.scrollToBottom();
  }

  showTypingIndicator() {
    const container = document.getElementById("copilot-messages");
    if (!container) return;

    const el = document.createElement("div");
    el.id = "copilot-typing";
    el.className = "copilot-msg copilot-assistant animate-fade-in";
    el.innerHTML = `
      <div class="msg-avatar"><i class="bi bi-robot"></i></div>
      <div class="msg-content">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    container.appendChild(el);
    this.scrollToBottom();
  }

  removeTypingIndicator() {
    document.getElementById("copilot-typing")?.remove();
  }

  scrollToBottom() {
    const container = document.getElementById("copilot-messages");
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }

  formatMarkdown(text) {
    if (!text) return "";
    let html = this.escapeHtml(text);
    // Replace **bold** with <strong>
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Replace * bullet with list items
    html = html.replace(/^\s*\*\s+(.*?)$/gm, "<li>$1</li>");
    // Wrap lists
    html = html.replace(/(<li>.*?<\/li>)/gs, "<ul>$1</ul>");
    // Clean multiple <ul> tags
    html = html.replace(/<\/ul>\s*<ul>/g, "");
    // Line breaks
    html = html.replace(/\n\n/g, "<br><br>");
    return html;
  }

  escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
  }
}

// Global initialization helper
window.initCopilot = function () {
  if (!window.vgCopilot) {
    window.vgCopilot = new VisionGuardCopilot();
    window.vgCopilot.init();
  }
  return window.vgCopilot;
};
