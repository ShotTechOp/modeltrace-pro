/**
 * ModelTrace Pro — 2D Latent Space Radar Visualizer
 * High-performance interactive HTML5 Canvas manifold visualizer
 */

(function () {
  const canvas = document.getElementById("latent-radar-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const tooltip = document.getElementById("radar-tooltip");
  const telemetryStatus = document.getElementById("radar-telemetry-status");
  const telemetryTarget = document.getElementById("radar-telemetry-target");
  const telemetryBearing = document.getElementById("radar-telemetry-bearing");
  const telemetryDist = document.getElementById("radar-telemetry-dist");
  const telemetryCluster = document.getElementById("radar-telemetry-cluster");

  let nodes = [];
  let families = {};
  let target = null;
  let activeFilter = "all";
  let hoveredNode = null;
  let sweepAngle = 0;
  let sweepEnabled = true;
  let pulseRadius = 0;

  // Viewport transforms (Pan & Zoom)
  let zoom = 1.0;
  let targetZoom = 1.0;
  let panX = 0;
  let panY = 0;
  let targetPanX = 0;
  let targetPanY = 0;
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;

  const FAMILY_COLORS = {
    claude: "#f59e0b",
    gpt: "#10b981",
    gemini: "#38bdf8",
    deepseek: "#06b6d4",
    grok: "#c084fc",
    llama: "#818cf8",
    qwen: "#fb7185",
    mistral: "#facc15",
    frontier: "#2dd4bf",
  };

  async function loadConstellation() {
    try {
      const res = await fetch("/api/radar/constellation");
      const data = await res.json();
      nodes = data.nodes || [];
      families = data.families || {};
      renderFilterPills();
    } catch (err) {
      console.error("Failed to load radar constellation:", err);
    }
  }

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(320, Math.floor(rect.width));
    const height = Math.max(320, Math.floor(rect.height));

    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }
  }

  function renderFilterPills() {
    const container = document.getElementById("radar-filter-pills");
    if (!container) return;

    const famKeys = Object.keys(families);
    let html = `<button type="button" class="radar-pill active" data-family="all">All Families (${nodes.length})</button>`;
    
    for (const k of famKeys) {
      const fam = families[k];
      const count = nodes.filter(n => n.family === k).length;
      html += `<button type="button" class="radar-pill" data-family="${k}">
        <span class="pill-dot" style="background: ${fam.color};"></span>
        <span>${fam.short} (${count})</span>
      </button>`;
    }
    container.innerHTML = html;

    container.querySelectorAll(".radar-pill").forEach(btn => {
      btn.addEventListener("click", () => {
        container.querySelectorAll(".radar-pill").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.family;
      });
    });
  }

  function updateTelemetry() {
    if (!telemetryStatus) return;

    if (!target) {
      telemetryStatus.textContent = "PASSIVE SCANNING";
      telemetryStatus.className = "telem-val status-scanning";
      if (telemetryTarget) telemetryTarget.textContent = "No Target Pinned";
      if (telemetryBearing) telemetryBearing.textContent = `${((sweepAngle * 180 / Math.PI) % 360).toFixed(1)}°`;
      if (telemetryDist) telemetryDist.textContent = "---";
      if (telemetryCluster) telemetryCluster.textContent = "All Constellations";
    } else if (target.status === "UNANCHORED_OOD") {
      telemetryStatus.textContent = "UNANCHORED DRIFT";
      telemetryStatus.className = "telem-val status-drift";
      if (telemetryTarget) telemetryTarget.textContent = target.label || "OOD Signature";
      if (telemetryBearing) telemetryBearing.textContent = `${target.angle_deg || 0}°`;
      if (telemetryDist) telemetryDist.textContent = `${target.r || 1.18} (OUT-OF-BOUNDS)`;
      if (telemetryCluster) telemetryCluster.textContent = `Near ${target.nearest_cluster || "Unknown"}`;
    } else {
      telemetryStatus.textContent = "TARGET ACQUIRED";
      telemetryStatus.className = "telem-val status-locked";
      if (telemetryTarget) telemetryTarget.textContent = `${target.label} (${target.confidence}%)`;
      if (telemetryBearing) telemetryBearing.textContent = `${target.angle_deg}°`;
      if (telemetryDist) telemetryDist.textContent = `${target.r} (Radial Orbit)`;
      if (telemetryCluster) telemetryCluster.textContent = target.nearest_cluster || "Frontier";
    }
  }

  function draw() {
    resizeCanvas();
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;
    const cx = w / 2 + panX;
    const cy = h / 2 + panY;
    const baseRadius = Math.min(w, h) * 0.42 * zoom;

    // Smooth pan/zoom interpolation
    panX += (targetPanX - panX) * 0.12;
    panY += (targetPanY - panY) * 0.12;
    zoom += (targetZoom - zoom) * 0.12;

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // Dark space background grid
    ctx.fillStyle = "#07090e";
    ctx.fillRect(0, 0, w, h);

    // Draw background radar concentric rings
    const rings = [0.25, 0.50, 0.75, 1.0, 1.25];
    const ringLabels = ["Core", "Inner Orbit", "Frontier Zone", "100% Boundary", "OOD Deep Space"];

    rings.forEach((ring, idx) => {
      const r = baseRadius * ring;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = idx === 3 ? "rgba(56, 189, 248, 0.45)" : (idx === 4 ? "rgba(239, 68, 68, 0.3)" : "rgba(255, 255, 255, 0.08)");
      ctx.lineWidth = idx === 3 ? 1.5 : 1;
      if (idx === 4) {
        ctx.setLineDash([4, 6]);
      } else {
        ctx.setLineDash([]);
      }
      ctx.stroke();
      ctx.setLineDash([]);

      // Ring text
      ctx.fillStyle = idx === 4 ? "rgba(239, 68, 68, 0.6)" : "rgba(148, 163, 184, 0.45)";
      ctx.font = "9px 'JetBrains Mono', monospace";
      ctx.textAlign = "left";
      ctx.fillText(ringLabels[idx], cx + 6, cy - r + 11);
    });

    // Degree spokes (every 45 degrees)
    for (let deg = 0; deg < 360; deg += 45) {
      const rad = deg * Math.PI / 180;
      const x2 = cx + Math.cos(rad) * baseRadius * 1.25;
      const y2 = cy + Math.sin(rad) * baseRadius * 1.25;

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = deg % 90 === 0 ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.05)";
      ctx.stroke();

      // Degree label
      const lx = cx + Math.cos(rad) * (baseRadius * 1.28);
      const ly = cy + Math.sin(rad) * (baseRadius * 1.28);
      ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
      ctx.font = "10px 'JetBrains Mono', monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(`${deg}°`, lx, ly);
    }

    // Family Sector Arc Labels
    for (const famKey in families) {
      const fam = families[famKey];
      const rad = fam.base_deg * Math.PI / 180;
      const lx = cx + Math.cos(rad) * (baseRadius * 1.10);
      const ly = cy + Math.sin(rad) * (baseRadius * 1.10);

      ctx.fillStyle = fam.color;
      ctx.font = "bold 10px 'Outfit', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(fam.short.toUpperCase(), lx, ly);
    }

    // Rotating Radar Sweep Beam
    if (sweepEnabled) {
      sweepAngle = (sweepAngle + 0.016) % (Math.PI * 2);
      const sweepLen = baseRadius * 1.25;

      // Trailing gradient cone
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, sweepLen);
      grad.addColorStop(0, "rgba(56, 189, 248, 0.25)");
      grad.addColorStop(1, "rgba(56, 189, 248, 0.0)");

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, sweepLen, sweepAngle - 0.35, sweepAngle);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();

      // Leading beam line
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(sweepAngle) * sweepLen, cy + Math.sin(sweepAngle) * sweepLen);
      ctx.strokeStyle = "rgba(56, 189, 248, 0.75)";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();
    }

    // Draw Constellation Lines for Active Filter
    if (activeFilter !== "all") {
      const famNodes = nodes.filter(n => n.family === activeFilter);
      if (famNodes.length > 1) {
        ctx.beginPath();
        famNodes.forEach((n, idx) => {
          const px = cx + n.x * baseRadius;
          const py = cy + n.y * baseRadius;
          if (idx === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.closePath();
        ctx.strokeStyle = (FAMILY_COLORS[activeFilter] || "#38bdf8") + "33";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // Draw Constellation Model Stars
    nodes.forEach(node => {
      const px = cx + node.x * baseRadius;
      const py = cy + node.y * baseRadius;
      const isFiltered = activeFilter !== "all" && node.family !== activeFilter;
      const isHovered = hoveredNode && hoveredNode.id === node.id;

      const alpha = isFiltered ? 0.18 : (isHovered ? 1.0 : 0.75);
      const color = node.color || FAMILY_COLORS[node.family] || "#94a3b8";

      // Outer glow
      ctx.beginPath();
      ctx.arc(px, py, isHovered ? 8 : 4.5, 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? color : `${color}${Math.floor(alpha * 255).toString(16).padStart(2, "0")}`;
      ctx.fill();

      // Center core
      ctx.beginPath();
      ctx.arc(px, py, isHovered ? 3.5 : 2, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();

      if (isHovered) {
        ctx.beginPath();
        ctx.arc(px, py, 12, 0, Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });

    // Draw Target Reticle if active
    if (target) {
      const tx = cx + target.x * baseRadius;
      const ty = cy + target.y * baseRadius;
      const isOOD = target.status === "UNANCHORED_OOD";
      const targetColor = isOOD ? "#ef4444" : (target.color || "#10b981");

      // Expanding sonar pulse wave
      pulseRadius = (pulseRadius + 0.5) % 35;
      ctx.beginPath();
      ctx.arc(tx, ty, 8 + pulseRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `${targetColor}${Math.floor((1 - pulseRadius / 35) * 200).toString(16).padStart(2, "0")}`;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Vector ray from center to target
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(tx, ty);
      ctx.strokeStyle = `${targetColor}44`;
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Tactical Target Crosshair Reticle
      ctx.save();
      ctx.translate(tx, ty);
      ctx.strokeStyle = targetColor;
      ctx.lineWidth = 2;

      // Reticle corners [ ]
      const sz = 12;
      ctx.beginPath();
      // Top-left
      ctx.moveTo(-sz, -sz + 5); ctx.lineTo(-sz, -sz); ctx.lineTo(-sz + 5, -sz);
      // Top-right
      ctx.moveTo(sz - 5, -sz); ctx.lineTo(sz, -sz); ctx.lineTo(sz, -sz + 5);
      // Bottom-left
      ctx.moveTo(-sz, sz - 5); ctx.lineTo(-sz, sz); ctx.lineTo(-sz + 5, sz);
      // Bottom-right
      ctx.moveTo(sz - 5, sz); ctx.lineTo(sz, sz); ctx.lineTo(sz, sz - 5);
      ctx.stroke();

      // Center dot
      ctx.beginPath();
      ctx.arc(0, 0, 3, 0, Math.PI * 2);
      ctx.fillStyle = targetColor;
      ctx.fill();

      // Target HUD Label tag
      const labelText = isOOD ? "⚠️ OOD UNANCHORED DRIFT" : `🎯 ${target.label} (${target.confidence}%)`;
      ctx.font = "bold 11px 'JetBrains Mono', monospace";
      const tm = ctx.measureText(labelText);
      const bgW = tm.width + 16;
      const bgH = 22;

      ctx.fillStyle = isOOD ? "rgba(239, 68, 68, 0.9)" : "rgba(15, 23, 42, 0.92)";
      ctx.strokeStyle = targetColor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(14, -bgH / 2, bgW, bgH, 4);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = isOOD ? "#ffffff" : targetColor;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(labelText, 22, 0);

      ctx.restore();
    }

    ctx.restore();

    updateTelemetry();
    requestAnimationFrame(draw);
  }

  // Interactivity Handlers
  canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (isDragging) {
      targetPanX += mouseX - dragStartX;
      targetPanY += mouseY - dragStartY;
      dragStartX = mouseX;
      dragStartY = mouseY;
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;
    const cx = w / 2 + panX;
    const cy = h / 2 + panY;
    const baseRadius = Math.min(w, h) * 0.42 * zoom;

    let closest = null;
    let minDist = 18;

    nodes.forEach(node => {
      if (activeFilter !== "all" && node.family !== activeFilter) return;
      const px = cx + node.x * baseRadius;
      const py = cy + node.y * baseRadius;
      const dist = Math.hypot(px - mouseX, py - mouseY);
      if (dist < minDist) {
        minDist = dist;
        closest = node;
      }
    });

    hoveredNode = closest;
    if (closest && tooltip) {
      tooltip.innerHTML = `
        <div class="tooltip-header">
          <strong style="color: ${closest.color};">${escapeHtml(closest.display_name)}</strong>
          <span class="badge-tag">${escapeHtml(closest.family_short)}</span>
        </div>
        <div class="tooltip-coords mono">θ: ${closest.angle_deg}° · Radius: ${closest.r}</div>
        <div class="tooltip-sub">Enrolled Reference Centroid</div>
      `;
      tooltip.style.left = `${mouseX + 14}px`;
      tooltip.style.top = `${mouseY + 14}px`;
      tooltip.classList.remove("hidden");
    } else if (tooltip) {
      tooltip.classList.add("hidden");
    }
  });

  canvas.addEventListener("mouseleave", () => {
    isDragging = false;
    hoveredNode = null;
    if (tooltip) tooltip.classList.add("hidden");
  });

  canvas.addEventListener("mousedown", (e) => {
    isDragging = true;
    const rect = canvas.getBoundingClientRect();
    dragStartX = e.clientX - rect.left;
    dragStartY = e.clientY - rect.top;
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
  });

  // Mobile Touch Support
  canvas.addEventListener("touchstart", (e) => {
    if (e.touches.length === 1) {
      isDragging = true;
      const rect = canvas.getBoundingClientRect();
      dragStartX = e.touches[0].clientX - rect.left;
      dragStartY = e.touches[0].clientY - rect.top;
    }
  }, { passive: true });

  canvas.addEventListener("touchmove", (e) => {
    if (isDragging && e.touches.length === 1) {
      const rect = canvas.getBoundingClientRect();
      const touchX = e.touches[0].clientX - rect.left;
      const touchY = e.touches[0].clientY - rect.top;
      targetPanX += touchX - dragStartX;
      targetPanY += touchY - dragStartY;
      dragStartX = touchX;
      dragStartY = touchY;
    }
  }, { passive: true });

  canvas.addEventListener("touchend", () => {
    isDragging = false;
  });

  canvas.addEventListener("dblclick", () => {
    targetZoom = 1.0;
    targetPanX = 0;
    targetPanY = 0;
  });

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 1.15 : 0.87;
    targetZoom = Math.max(0.6, Math.min(3.5, targetZoom * delta));
  }, { passive: false });

  // Floating Controls
  const btnZoomIn = document.getElementById("radar-btn-zoomin");
  const btnZoomOut = document.getElementById("radar-btn-zoomout");
  const btnReset = document.getElementById("radar-btn-reset");
  const btnFocus = document.getElementById("radar-btn-focus");
  const btnSweep = document.getElementById("radar-btn-sweep");

  if (btnZoomIn) btnZoomIn.addEventListener("click", () => { targetZoom = Math.min(3.5, targetZoom * 1.25); });
  if (btnZoomOut) btnZoomOut.addEventListener("click", () => { targetZoom = Math.max(0.6, targetZoom * 0.8); });
  if (btnReset) btnReset.addEventListener("click", () => { targetZoom = 1.0; targetPanX = 0; targetPanY = 0; });
  if (btnSweep) btnSweep.addEventListener("click", () => {
    sweepEnabled = !sweepEnabled;
    btnSweep.classList.toggle("active", sweepEnabled);
  });
  if (btnFocus) btnFocus.addEventListener("click", () => {
    focusRadarOnTarget();
  });

  function focusRadarOnTarget() {
    if (!target) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;
    const baseRadius = Math.min(w, h) * 0.42;

    targetZoom = 1.6;
    targetPanX = -target.x * baseRadius * targetZoom;
    targetPanY = -target.y * baseRadius * targetZoom;
  }

  function setRadarTarget(coord) {
    target = coord;
    updateTelemetry();
  }

  function escapeHtml(str) {
    return String(str || "").replace(/[&<>'"]/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
    })[c]);
  }

  // Export to window
  window.LatentRadar = {
    init: loadConstellation,
    setTarget: setRadarTarget,
    focusTarget: focusRadarOnTarget,
  };

  // Start radar
  loadConstellation();
  requestAnimationFrame(draw);
})();
