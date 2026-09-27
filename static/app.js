const state = {
  challenges: [],
  bankId: window.DEFAULT_BANK_ID,
  bank: window.BANK_SUMMARIES ? window.BANK_SUMMARIES[window.DEFAULT_BANK_ID] : null,
  unified: window.UNIFIED_SUMMARY,
  lastAuditResult: null,
};

const byId = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function percent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function optionalNumber(id) {
  const value = byId(id).value.trim();
  return value === "" ? null : Number(value);
}

function setMessage(element, text, type = "error") {
  element.textContent = text;
  element.className = `message-banner ${type}`;
  element.hidden = !text;
}

function togglePasswordVisibility(id) {
  const input = byId(id);
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
}

function fillPreset(url, model) {
  byId("test-api-base").value = url;
  byId("test-api-model").value = model;
  const keyInput = byId("test-api-key");
  if (!keyInput.value) {
    keyInput.focus();
  }
}

function activateWorkspace(name) {
  document.querySelectorAll(".workspace").forEach((item) => item.classList.toggle("active", item.id === `workspace-${name}`));
  document.querySelectorAll("[data-workspace]").forEach((item) => item.classList.toggle("active", item.dataset.workspace === name));
}

function activateMode(group, name) {
  document.querySelectorAll(`[data-${group}-mode]`).forEach((item) => item.classList.toggle("active", item.dataset[`${group}Mode`] === name));
  document.querySelectorAll(`#workspace-${group === "test" ? "test" : "library"} .mode-panel`).forEach((item) => {
    item.classList.toggle("active", item.id === `${group}-${name}` || item.id === `library-${name}`);
  });
}

async function loadChallenges() {
  const btn = byId("regenerate");
  if (btn) btn.disabled = true;
  byId("result").hidden = true;
  setMessage(byId("test-message"), "");
  try {
    const response = await fetch("/api/challenges");
    state.challenges = (await response.json()).challenges;
    renderChallenges();
  } catch (err) {
    setMessage(byId("test-message"), "Failed to load challenges: " + err.message, "error");
  }
  if (btn) btn.disabled = false;
}

function renderChallenges() {
  const container = byId("challenge-list");
  if (!container) return;
  container.innerHTML = state.challenges.map((challenge, index) => `
    <article class="challenge-item">
      <div class="challenge-header">
        <strong>Challenge Probe #${index + 1}</strong>
        <span>Target: ${challenge.expected_count} integers</span>
        <button type="button" data-copy="${index}">Copy Prompt</button>
      </div>
      <div class="challenge-columns">
        <div>
          <label class="label-title">Send to Model</label>
          <pre>${escapeHtml(challenge.prompt)}</pre>
        </div>
        <div>
          <label class="label-title" for="output-${index}">Paste Model's Output</label>
          <textarea id="output-${index}" spellcheck="false" placeholder="Paste unedited output sequence here..."></textarea>
        </div>
      </div>
    </article>
  `).join("");

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const idx = Number(button.dataset.copy);
      await navigator.clipboard.writeText(state.challenges[idx].prompt);
      const originalText = button.textContent;
      button.textContent = "Copied ✓";
      button.style.borderColor = "var(--emerald)";
      button.style.color = "var(--emerald)";
      window.setTimeout(() => {
        button.textContent = originalText;
        button.style.borderColor = "";
        button.style.color = "";
      }, 1500);
    });
  });
}

function renderResult(payload, claimedModel = null) {
  state.lastAuditResult = { payload, claimedModel };

  // Detect spoofing
  const predicted = (payload.prediction_name || "").toLowerCase();
  const claimed = (claimedModel || "").toLowerCase().trim();
  
  let isSpoof = false;
  if (claimed) {
    // If user claimed Opus or Sonnet or GPT-4o but prediction is different
    const isClaimedHaiku = claimed.includes("haiku") || claimed.includes("flash");
    const isPredHaiku = predicted.includes("haiku") || predicted.includes("flash") || predicted.includes("mini");
    const isClaimedOpus = claimed.includes("opus");
    const isPredOpus = predicted.includes("opus");

    if ((isClaimedOpus && !isPredOpus) || (isClaimedOpus && isPredHaiku) || (!isClaimedHaiku && isPredHaiku)) {
      isSpoof = true;
    } else if (claimed && !claimed.includes(predicted) && !predicted.includes(claimed)) {
      isSpoof = true;
    }
  }

  // Diagnostics chips
  const diagnostics = payload.diagnostics.map((item, index) => `
    <span class="diagnostic-chip ${item.accepted ? "accepted" : "rejected"}">
      Probe #${index + 1}: ${item.parsed_numbers} numbers · ${item.accepted ? "Valid ✓" : "Invalid ✗"}
    </span>
  `).join("");

  // Table rows
  const rows = payload.results.map((item, index) => `
    <tr class="${index === 0 ? "winner" : ""}">
      <td>#${index + 1}</td>
      <td><strong>${escapeHtml(item.display_name)}</strong></td>
      <td><span class="badge-subtle">${escapeHtml(item.family_name)}</span></td>
      <td>
        <div class="prob-bar-container">
          <div class="prob-track">
            <span class="prob-fill" style="width: ${Math.max(2, item.probability * 100)}%"></span>
          </div>
          <strong>${percent(item.probability)}</strong>
        </div>
      </td>
      <td><code>${percent(item.profile_similarity)}</code></td>
    </tr>
  `).join("");

  const apiMeta = payload.api_test || {};

  byId("result").innerHTML = `
    <div class="hero-attribution-card ${payload.is_ood ? 'ood-detected' : (isSpoof ? 'spoof-detected' : 'authentic')}">
      <div class="audit-status-badge ${payload.is_ood ? 'ood' : (isSpoof ? 'warning' : 'verified')}">
        ${payload.is_ood
          ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> UNANCHORED SIGNATURE / UN-ENROLLED MODEL'
          : (isSpoof 
              ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> SPOOFING / ROUTER SWAP DETECTED' 
              : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg> AUTHENTIC FINGERPRINT MATCH')}
      </div>

      <div class="hero-main-row">
        <div>
          <div class="hero-model-title">${escapeHtml(payload.prediction_name)}</div>
          <div class="hero-family-tag">Identified Family: <strong>${escapeHtml(payload.family_prediction_name)}</strong> (${percent(payload.family_probability)})</div>
        </div>

        <div class="hero-probability-gauge">
          <div class="gauge-num">${percent(payload.probability)}</div>
          <div class="gauge-label">${payload.is_ood ? 'Relative Fit (OOD)' : 'Attribution Confidence'}</div>
        </div>
      </div>

      ${payload.is_ood ? `
        <div class="ood-alert-box">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          <div>
            <strong>Potential Un-enrolled Model Architecture (${escapeHtml(payload.ood_reason || 'Low Centroid Similarity')})</strong>
            <p>The statistical characteristics of these outputs deviate from enrolled reference centroids. While <strong>${escapeHtml(payload.prediction_name)}</strong> is the nearest mathematical match, the low similarity (${percent(payload.top_similarity || payload.results[0]?.profile_similarity)}) suggests this response likely originates from an un-enrolled architecture, custom quantization, or heavy post-processing.</p>
          </div>
        </div>
      ` : (isSpoof ? `
        <div class="spoof-alert-box">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          <div>
            <strong>Provider Discrepancy Alert!</strong>
            <p>You requested <strong>${escapeHtml(claimedModel || "Custom Model")}</strong>, but the mathematical fingerprinting algorithm indicates the response was fulfilled by <strong>${escapeHtml(payload.prediction_name)}</strong>. The provider is likely routing your requests through a cheaper lightweight model.</p>
          </div>
        </div>
      ` : '')}
    </div>

    <!-- Stats Summary Row -->
    <div class="stats-summary-row">
      <div class="stat-box">
        <span>Profile Similarity</span>
        <strong>${percent(payload.results[0]?.profile_similarity)}</strong>
      </div>
      <div class="stat-box">
        <span>Valid Samples</span>
        <strong>${payload.used_outputs} / 3</strong>
      </div>
      <div class="stat-box">
        <span>Avg Generation Speed</span>
        <strong>${apiMeta.avg_tps ? apiMeta.avg_tps + ' tps' : 'N/A'}</strong>
      </div>
      <div class="stat-box">
        <span>Avg Latency</span>
        <strong>${apiMeta.avg_lat ? apiMeta.avg_lat + ' s' : 'N/A'}</strong>
      </div>
    </div>

    <!-- Diagnostic Badges -->
    <div class="diagnostics-chips">${diagnostics}</div>

    <!-- Candidates Table -->
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Candidate Model</th>
            <th>Family</th>
            <th>Attribution Probability</th>
            <th>Centroid Similarity</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>

    <!-- Forensic Action Toolbar -->
    <div class="results-action-toolbar">
      <button class="button secondary" type="button" onclick="copyMarkdownReport()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        Copy Forensic Report (Markdown)
      </button>
    </div>
  `;

  byId("result").hidden = false;
  byId("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

function copyMarkdownReport() {
  if (!state.lastAuditResult) return;
  const { payload, claimedModel } = state.lastAuditResult;
  const isSpoof = claimedModel && !claimedModel.toLowerCase().includes(payload.prediction_name.toLowerCase());
  
  let md = `### 🔍 ModelTrace Forensic Attribution Audit\n\n`;
  md += `- **Claimed / Billed Model**: \`${claimedModel || "Not specified"}\`\n`;
  md += `- **Attributed Real Model**: \`${payload.prediction_name}\` (${percent(payload.probability)} confidence)\n`;
  md += `- **Model Family**: \`${payload.family_prediction_name}\`\n`;
  md += `- **Verdict**: ${isSpoof ? '🚨 **MODEL SPOOFING DETECTED** (Provider returned mismatched model)' : '✅ **AUTHENTIC MATCH**'}\n\n`;
  
  md += `| Rank | Candidate Model | Family | Probability | Centroid Similarity |\n`;
  md += `| :--- | :--- | :--- | :--- | :--- |\n`;
  payload.results.slice(0, 5).forEach((r, idx) => {
    md += `| #${idx + 1} | **${r.display_name}** | ${r.family_name} | ${percent(r.probability)} | ${percent(r.profile_similarity)} |\n`;
  });
  
  if (payload.api_test) {
    md += `\n*Audited via ModelTrace API probes: ${payload.api_test.received}/${payload.api_test.requested} samples valid, Avg Speed: ${payload.api_test.avg_tps || 'N/A'} tps.*`;
  }

  navigator.clipboard.writeText(md).then(() => {
    alert("Forensic Markdown report copied to clipboard!");
  });
}

async function analyzeManual() {
  const button = byId("analyze");
  button.disabled = true;
  setMessage(byId("test-message"), "Computing mathematical Hellinger projections...", "working");
  
  const outputs = state.challenges.map((challenge, index) => ({
    text: byId(`output-${index}`).value,
    expected_count: challenge.expected_count,
  }));

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outputs })
    });
    const payload = await response.json();
    if (response.ok) {
      setMessage(byId("test-message"), "");
      renderResult(payload);
    } else {
      setMessage(byId("test-message"), payload.error || "Attribution computation failed.", "error");
      byId("result").hidden = true;
    }
  } catch (err) {
    setMessage(byId("test-message"), "Error: " + err.message, "error");
  }
  button.disabled = false;
}

function renderApiProgress(states, status) {
  const valid = states.filter((state) => state === "done").length;
  const attempted = states.filter((state) => ["done", "invalid", "error"].includes(state)).length;
  const target = 3;
  byId("api-test-progress").hidden = false;
  byId("api-progress-status").textContent = status;
  byId("api-progress-count").textContent = `${valid}/${target} Valid · ${attempted}/${states.length} Attempts`;
  byId("api-progress-fill").style.width = `${(valid / target) * 100}%`;
  
  byId("api-progress-steps").innerHTML = states.map((state, index) => {
    const labels = {
      pending: "Waiting",
      working: "Probing...",
      done: "Accepted",
      invalid: "Count Insufficient",
      error: "API Failed",
      skipped: "Skipped"
    };
    return `<span class="progress-step ${state}"><b>${index + 1}</b>Probe #${index + 1} · ${labels[state]}</span>`;
  }).join("");
}

async function testViaApi(event) {
  event.preventDefault();
  const button = byId("btn-start-audit");
  button.disabled = true;
  byId("result").hidden = true;
  setMessage(byId("test-message"), "");

  // Show telemetry grid
  const telemGrid = byId("api-telemetry-grid");
  telemGrid.hidden = false;
  byId("telem-tps").textContent = "-- tps";
  byId("telem-lat").textContent = "-- s";
  byId("telem-format").textContent = "Auto";
  byId("telem-leak").textContent = "Clean";
  byId("telem-leak-card").classList.remove("leak-alert");

  let firstBatch = [];
  try {
    const challengeResponse = await fetch("/api/challenges");
    firstBatch = (await challengeResponse.json()).challenges;
  } catch (err) {
    setMessage(byId("test-message"), "Failed to generate challenge suite: " + err.message, "error");
    button.disabled = false;
    return;
  }

  const retryResponse = await fetch("/api/challenges");
  const challenges = firstBatch.concat((await retryResponse.json()).challenges);
  const states = challenges.map(() => "pending");
  const outputs = [];
  const errors = [];
  const target = 3;

  const claimedModel = byId("test-api-model").value.trim();
  const configuration = {
    base_url: byId("test-api-base").value.trim(),
    api_key: byId("test-api-key").value.trim(),
    api_model: claimedModel,
    temperature: optionalNumber("test-temperature"),
  };

  const latencies = [];
  const tpsList = [];
  let leakedModel = null;
  let detectedFormat = "Auto";

  renderApiProgress(states, "Challenges generated. Dispatching probes to model...");

  for (let index = 0; index < challenges.length && outputs.length < target; index += 1) {
    states[index] = "working";
    renderApiProgress(states, `Dispatching Probe #${index + 1} (${challenges[index].expected_count} ints)...`);
    
    try {
      const response = await fetch("/api/test/probe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...configuration,
          prompt: challenges[index].prompt,
          expected_count: challenges[index].expected_count,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "API request rejected");

      // Record Telemetry
      if (payload.latency) latencies.push(payload.latency);
      if (payload.tps) tpsList.push(payload.tps);
      if (payload.api_format) detectedFormat = payload.api_format;
      if (payload.model_leak) leakedModel = payload.model_leak;

      // Update Live Telemetry Cards
      if (tpsList.length) {
        const avgTps = (tpsList.reduce((a, b) => a + b, 0) / tpsList.length).toFixed(1);
        byId("telem-tps").textContent = `${avgTps} tps`;
        byId("telem-tps-note").textContent = avgTps > 85 ? "⚡ Very Fast (Likely Haiku/Mini)" : "Normal latency curve";
      }
      if (latencies.length) {
        const avgLat = (latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(2);
        byId("telem-lat").textContent = `${avgLat} s`;
      }
      byId("telem-format").textContent = detectedFormat === "anthropic" ? "Anthropic" : "OpenAI";
      if (leakedModel) {
        byId("telem-leak").textContent = leakedModel;
        byId("telem-leak-note").textContent = "Mismatch detected!";
        byId("telem-leak-card").classList.add("leak-alert");
      }

      if (payload.accepted) {
        outputs.push({ text: payload.text, expected_count: challenges[index].expected_count });
        states[index] = "done";
      } else {
        errors.push(`Probe #${index + 1}: Parsed ${payload.parsed_numbers}/${payload.minimum_numbers} ints`);
        states[index] = "invalid";
      }
    } catch (error) {
      errors.push(`Probe #${index + 1}: ${error.message}`);
      states[index] = "error";
    }
    renderApiProgress(states, `Acquired ${outputs.length}/${target} valid samples`);
  }

  if (outputs.length === target) {
    states.forEach((state, index) => { if (state === "pending") states[index] = "skipped"; });
  }

  if (!outputs.length) {
    renderApiProgress(states, "All 6 attempts failed to return valid outputs");
    setMessage(byId("test-message"), `No valid outputs collected. ${errors[0] || ""}`, "error");
    button.disabled = false;
    return;
  }

  renderApiProgress(states, "Samples acquired. Computing Hellinger distance & ordered features...");
  
  try {
    const analysisResponse = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outputs }),
    });
    const result = await analysisResponse.json();
    if (analysisResponse.ok) {
      const attempted = states.filter((state) => ["done", "invalid", "error"].includes(state)).length;
      result.api_test = {
        requested: target,
        attempted,
        max_attempts: challenges.length,
        received: outputs.length,
        errors,
        avg_tps: tpsList.length ? (tpsList.reduce((a, b) => a + b, 0) / tpsList.length).toFixed(1) : null,
        avg_lat: latencies.length ? (latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(2) : null,
        leaked_model: leakedModel,
      };
      renderApiProgress(states, `Audit Complete: ${outputs.length}/${target} samples attributed`);
      renderResult(result, claimedModel);
    } else {
      setMessage(byId("test-message"), result.error || "Analysis failed.", "error");
    }
  } catch (err) {
    setMessage(byId("test-message"), "Analysis request failed: " + err.message, "error");
  }

  button.disabled = false;
}

function updateUnifiedSummary(summary) {
  if (!summary) return;
  state.unified = summary;
  const countEl = byId("topbar-bank-count");
  if (countEl) countEl.textContent = `${summary.model_count} Candidate Models in Bank`;
  const badgeEl = byId("active-bank-badge");
  if (badgeEl) badgeEl.innerHTML = `<span class="dot"></span> ${summary.model_count} Verified Models in Bank`;
}

function renderInventory() {
  if (!state.bank) return;
  byId("selected-bank-name").textContent = `${state.bank.label} Family Models`;
  const modelOptions = byId("model-options");
  if (modelOptions) {
    modelOptions.innerHTML = state.bank.models.map((m) => `<option value="${escapeHtml(m.id)}"></option>`).join("");
  }
  const inv = byId("bank-inventory");
  if (inv) {
    inv.innerHTML = state.bank.models.length
      ? state.bank.models.map((model) => `
        <div class="fingerprint-card">
          <strong>${escapeHtml(model.display_name)}</strong>
          <span>ID: <code>${escapeHtml(model.id)}</code></span>
        </div>
      `).join("")
      : `<span class="empty-inventory">No models registered in this family yet.</span>`;
  }
}

async function refreshBank() {
  const response = await fetch(`/api/bank?bank_id=${encodeURIComponent(state.bankId)}`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Failed to load bank");
  state.bank = payload;
  renderInventory();
}

async function selectBank(bankId) {
  state.bankId = bankId;
  await refreshBank();
}

function renderBankOptions(summaries, selected) {
  byId("bank-select").innerHTML = Object.entries(summaries)
    .map(([bankId, bank]) => `<option value="${escapeHtml(bankId)}"${bankId === selected ? " selected" : ""}>${escapeHtml(bank.label)}</option>`)
    .join("");
}

async function createBank(event) {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const response = await fetch("/api/banks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: byId("new-bank-name").value }),
    });
    const payload = await response.json();
    if (response.ok) {
      window.BANK_SUMMARIES = payload.banks;
      state.bankId = payload.bank.id;
      state.bank = payload.bank;
      updateUnifiedSummary(payload.unified);
      renderBankOptions(payload.banks, state.bankId);
      renderInventory();
      byId("new-bank-name").value = "";
      byId("create-bank-form").hidden = true;
      setMessage(byId("enrollment-message"), `Created family: ${payload.bank.label}`, "success");
    } else {
      setMessage(byId("enrollment-message"), payload.error || "Creation failed.", "error");
    }
  } catch (err) {
    setMessage(byId("enrollment-message"), err.message, "error");
  }
  button.disabled = false;
}

// Bind Event Listeners
document.querySelectorAll("[data-workspace]").forEach((button) => {
  button.addEventListener("click", () => activateWorkspace(button.dataset.workspace));
});
document.querySelectorAll("[data-test-mode]").forEach((button) => {
  button.addEventListener("click", () => activateMode("test", button.dataset.testMode));
});
if (byId("bank-select")) {
  byId("bank-select").addEventListener("change", (event) => selectBank(event.target.value));
}
if (byId("regenerate")) {
  byId("regenerate").addEventListener("click", loadChallenges);
}
if (byId("analyze")) {
  byId("analyze").addEventListener("click", analyzeManual);
}
if (byId("api-test-form")) {
  byId("api-test-form").addEventListener("submit", testViaApi);
}
if (byId("show-create-bank")) {
  byId("show-create-bank").addEventListener("click", () => {
    byId("create-bank-form").hidden = !byId("create-bank-form").hidden;
  });
}
if (byId("create-bank-form")) {
  byId("create-bank-form").addEventListener("submit", createBank);
}

// Initial Run
renderInventory();
loadChallenges();
