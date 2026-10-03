/**
 * app.js - Frontend client logic for the Smart Guided Troubleshooting Engine.
 */

document.addEventListener("DOMContentLoaded", () => {
  const queryInput = document.getElementById("queryInput");
  const domainSelect = document.getElementById("domainSelect");
  const troubleshootBtn = document.getElementById("troubleshootBtn");
  const clearCacheBtn = document.getElementById("clearCacheBtn");
  const loadingSpinner = document.getElementById("loadingSpinner");
  const resultsSection = document.getElementById("resultsSection");

  const cacheBadge = document.getElementById("cacheBadge");
  const latencyValue = document.getElementById("latencyValue");
  const scoreValue = document.getElementById("scoreValue");
  const goalDisplay = document.getElementById("goalDisplay");
  const titleDisplay = document.getElementById("titleDisplay");
  const actionsList = document.getElementById("actionsList");
  const variationCountDisplay = document.getElementById("variationCountDisplay");
  const variationsGrid = document.getElementById("variationsGrid");
  const jsonViewer = document.getElementById("jsonViewer");

  // Sample query buttons
  document.querySelectorAll(".sample-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      queryInput.value = btn.dataset.query;
      domainSelect.value = btn.dataset.domain;
      triggerTroubleshoot();
    });
  });

  // Troubleshoot button click
  troubleshootBtn.addEventListener("click", () => {
    triggerTroubleshoot();
  });

  // Clear cache click
  clearCacheBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/v1/cache/clear", { method: "POST" });
      const data = await res.json();
      alert("Fast-path semantic cache cleared successfully!");
    } catch (err) {
      alert("Failed to clear cache: " + err.message);
    }
  });

  // Trigger troubleshooting request
  async function triggerTroubleshoot() {
    const query = queryInput.value.trim();
    if (!query) {
      alert("Please enter a troubleshooting query.");
      return;
    }

    const domain = domainSelect.value || null;

    // Show loading state
    loadingSpinner.classList.remove("hidden");
    troubleshootBtn.disabled = true;

    try {
      const response = await fetch("/v1/troubleshoot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          domain: domain
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Server error");
      }

      const data = await response.json();
      renderResults(data);
    } catch (err) {
      alert("Troubleshooting error: " + err.message);
    } finally {
      loadingSpinner.classList.add("hidden");
      troubleshootBtn.disabled = false;
    }
  }

  // Render plan results
  function renderResults(data) {
    resultsSection.style.display = "block";

    const meta = data.metadata || {};
    const context = (data.contexts && data.contexts[0]) || {};

    // Cache status
    if (meta.cache_hit) {
      cacheBadge.textContent = "HIT (" + (meta.cache_hit_type || "SEMANTIC") + ")";
      cacheBadge.className = "badge badge-hit";
    } else {
      cacheBadge.textContent = "MISS (COLD)";
      cacheBadge.className = "badge badge-miss";
    }

    latencyValue.textContent = (meta.latency_ms || 0) + " ms";
    scoreValue.textContent = context.score ? context.score.toFixed(2) : "0.00";

    goalDisplay.textContent = context.goal || "Follow these steps...";
    titleDisplay.textContent = context.title || "Troubleshooting Goal";

    // Render Actions
    actionsList.innerHTML = "";
    (context.action || []).forEach((act, actIdx) => {
      const actionCard = document.createElement("div");
      actionCard.className = "action-card";

      const catBadgeClass = "badge-cat-" + (act.category || "auto");
      const stepsHtml = (act.stepGroups || [])
        .map((sg) => {
          const stepsListHtml = (sg.steps || [])
            .map((s) => `<li>${escapeHtml(s)}</li>`)
            .join("");

          let deeplinkHtml = "";
          if (sg.actionableDeeplink) {
            deeplinkHtml = `
              <div class="deeplink-badge-row">
                <span class="label">Actionable Deeplink:</span>
                <code class="deeplink-uri">${escapeHtml(sg.actionableDeeplink)}</code>
              </div>
            `;
          } else if (act.category === "manual") {
            deeplinkHtml = `
              <div class="deeplink-badge-row">
                <span class="label" style="color: var(--badge-manual);">Physical Intervention Required (No in-device deeplink)</span>
              </div>
            `;
          }

          return `<ol class="steps-list">${stepsListHtml}</ol>${deeplinkHtml}`;
        })
        .join("");

      actionCard.innerHTML = `
        <div class="action-header">
          <div class="action-title-group">
            <h3>${escapeHtml(act.actionName)}</h3>
            <p class="action-desc">${escapeHtml(act.description)}</p>
          </div>
          <span class="badge ${catBadgeClass}">${act.category}</span>
        </div>
        ${stepsHtml}
      `;

      actionsList.appendChild(actionCard);
    });

    // Render Query Variations
    const variations = meta.query_variations || [];
    variationCountDisplay.textContent = variations.length;
    variationsGrid.innerHTML = "";

    variations.forEach((v) => {
      const chip = document.createElement("div");
      chip.className = "variation-chip";
      chip.innerHTML = `
        <div class="reg-label">${escapeHtml(v.register || "variation")}</div>
        <div class="reg-text">${escapeHtml(v.text)}</div>
      `;
      variationsGrid.appendChild(chip);
    });

    // Render JSON Contract
    jsonViewer.textContent = JSON.stringify(data, null, 2);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
