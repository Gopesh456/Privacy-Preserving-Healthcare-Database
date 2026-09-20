/**
 * PP-HDB: Privacy-Preserving Healthcare Database
 * Frontend Controller & Interaction Engine
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const roleSelect = document.getElementById("role-select");
  const purposeSelect = document.getElementById("purpose-select");
  const budgetVal = document.getElementById("budget-val");
  const budgetFill = document.getElementById("budget-bar-fill");
  const btnResetBudget = document.getElementById("btn-reset-budget");

  const sliderEpsilon = document.getElementById("slider-epsilon");
  const epsilonDisplay = document.getElementById("epsilon-display");
  const epsilonGuide = document.getElementById("epsilon-guide");

  const toggleDp = document.getElementById("toggle-dp");
  const toggleSmpc = document.getElementById("toggle-smpc");
  const toggleSuppression = document.getElementById("toggle-suppression");

  const queryForm = document.getElementById("query-form");
  const btnRunQuery = document.getElementById("btn-run-query");
  const resultsPlaceholder = document.getElementById("results-placeholder");
  const resultsContent = document.getElementById("results-content");
  const queryStatusBadge = document.getElementById("query-status-badge");

  // Presets
  const presetButtons = document.querySelectorAll(".btn-preset");

  // Vault Tabs
  const vaultTabs = document.querySelectorAll(".vault-tab");
  const vaultHeaders = document.getElementById("vault-headers");
  const vaultBody = document.getElementById("vault-body");

  // Anonymizer
  const btnExportAnon = document.getElementById("btn-export-anonymized");
  const anonCondition = document.getElementById("anon-condition");
  const anonK = document.getElementById("anon-k");
  const anonL = document.getElementById("anon-l");
  const anonResults = document.getElementById("anon-results");
  const anonTotalIn = document.getElementById("anon-total-in");
  const anonRetained = document.getElementById("anon-retained");
  const anonSuppressed = document.getElementById("anon-suppressed");
  const anonTbody = document.getElementById("anon-tbody");

  // Audit
  const btnVerifyChain = document.getElementById("btn-verify-chain");
  const btnSimulateTamper = document.getElementById("btn-simulate-tamper");
  const btnRestoreChain = document.getElementById("btn-restore-chain");
  const chainIntegrityBadge = document.getElementById("chain-integrity-badge");
  const blocksContainer = document.getElementById("blocks-container");

  // ==========================================
  // 1. Initial State & Data Fetching
  // ==========================================
  async function init() {
    await fetchNodeStats();
    await fetchBudget();
    await loadVault("node_a");
    await fetchAuditBlocks();
    setupSliderGuide();
  }

  async function fetchNodeStats() {
    try {
      const res = await fetch("/api/nodes");
      const data = await res.json();
      if (data.success) {
        data.nodes.forEach(node => {
          if (node.node_id === "node_a") document.getElementById("node-a-count").innerText = node.total_records;
          if (node.node_id === "node_b") document.getElementById("node-b-count").innerText = node.total_records;
          if (node.node_id === "node_c") document.getElementById("node-c-count").innerText = node.total_records;
        });
      }
    } catch (err) {
      console.error("Failed to fetch node statistics:", err);
    }
  }

  async function fetchBudget() {
    try {
      const res = await fetch("/api/budget");
      const data = await res.json();
      if (data.success) {
        updateBudgetUI(data.budget);
      }
    } catch (err) {
      console.error("Failed to fetch budget:", err);
    }
  }

  function updateBudgetUI(budget) {
    budgetVal.innerText = `${budget.remaining_budget.toFixed(2)} / ${budget.total_budget.toFixed(1)}`;
    const pct = Math.max(0, Math.min(100, (budget.remaining_budget / budget.total_budget) * 100));
    budgetFill.style.width = `${pct}%`;

    if (pct < 20) {
      budgetFill.style.background = "var(--accent-rose)";
    } else if (pct < 50) {
      budgetFill.style.background = "var(--accent-amber)";
    } else {
      budgetFill.style.background = "linear-gradient(90deg, var(--accent-purple), var(--accent-cyan))";
    }
  }

  btnResetBudget.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/budget/reset", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        updateBudgetUI(data.budget);
        alert("Privacy Budget (ε) successfully reset to 10.0.");
      }
    } catch (err) {
      console.error("Error resetting budget:", err);
    }
  });

  // ==========================================
  // 2. Slider & Guidance
  // ==========================================
  function setupSliderGuide() {
    sliderEpsilon.addEventListener("input", () => {
      const val = parseFloat(sliderEpsilon.value);
      epsilonDisplay.innerText = val.toFixed(2);

      if (val <= 0.2) {
        epsilonGuide.innerText = "Ultra-Strict Privacy (Heavy Laplace Noise)";
        epsilonGuide.style.color = "var(--accent-rose)";
      } else if (val <= 0.8) {
        epsilonGuide.innerText = "Strong Privacy (Substantial Noise)";
        epsilonGuide.style.color = "var(--accent-amber)";
      } else if (val <= 2.0) {
        epsilonGuide.innerText = "Balanced Tradeoff (Standard Clinical Research)";
        epsilonGuide.style.color = "var(--accent-cyan)";
      } else {
        epsilonGuide.innerText = "High Utility / Lower Privacy (Minimal Noise)";
        epsilonGuide.style.color = "var(--accent-emerald)";
      }
    });
  }

  // ==========================================
  // 3. Clinical Presets
  // ==========================================
  const PRESETS = {
    "diabetes-metformin": {
      condition: "Type-2 Diabetes",
      severity: "",
      biomarker: "",
      abnormal: "false",
      medication: "Metformin",
      outcome: "Positive",
      epsilon: 1.00
    },
    "htn-lisinopril": {
      condition: "Essential Hypertension",
      severity: "",
      biomarker: "Systolic BP",
      abnormal: "false",
      medication: "Lisinopril",
      outcome: "Positive",
      epsilon: 1.00
    },
    "cad-statin": {
      condition: "Coronary Artery Disease",
      severity: "Moderate",
      biomarker: "LDL-C",
      abnormal: "false",
      medication: "Atorvastatin",
      outcome: "",
      epsilon: 1.50
    },
    "asthma-fluticasone": {
      condition: "Bronchial Asthma",
      severity: "",
      biomarker: "FEV1/FVC",
      abnormal: "false",
      medication: "Fluticasone",
      outcome: "Positive",
      epsilon: 0.80
    }
  };

  presetButtons.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      presetButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const key = btn.dataset.preset;
      const p = PRESETS[key];
      if (!p) return;

      document.getElementById("filter-condition").value = p.condition;
      document.getElementById("filter-severity").value = p.severity;
      document.getElementById("filter-biomarker").value = p.biomarker;
      document.getElementById("filter-abnormal").value = p.abnormal;
      document.getElementById("filter-medication").value = p.medication;
      document.getElementById("filter-outcome").value = p.outcome;
      sliderEpsilon.value = p.epsilon;
      sliderEpsilon.dispatchEvent(new Event("input"));
    });
  });

  // ==========================================
  // 4. Federated Topology Animation
  // ==========================================
  function triggerTopologyPulse() {
    const pA = document.getElementById("pulse-a");
    const pB = document.getElementById("pulse-b");
    const pC = document.getElementById("pulse-c");

    [pA, pB, pC].forEach(p => {
      p.setAttribute("opacity", "1");
    });

    let progress = 0;
    const interval = setInterval(() => {
      progress += 0.05;
      if (progress >= 1) {
        clearInterval(interval);
        [pA, pB, pC].forEach(p => p.setAttribute("opacity", "0"));
      } else {
        // Linear interpolation towards center (480, 130)
        pA.setAttribute("cx", 160 + (480 - 160) * progress);
        pA.setAttribute("cy", 70 + (130 - 70) * progress);

        pB.setAttribute("cx", 160 + (480 - 160) * progress);
        pB.setAttribute("cy", 190 + (130 - 190) * progress);

        pC.setAttribute("cx", 800 + (480 - 800) * progress);
        pC.setAttribute("cy", 130);
      }
    }, 30);
  }

  // ==========================================
  // 5. Query Execution
  // ==========================================
  queryForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    btnRunQuery.disabled = true;
    btnRunQuery.innerHTML = `<span class="btn-icon">⏳</span> Executing Privacy Pipeline...`;
    queryStatusBadge.innerText = "Querying...";
    queryStatusBadge.className = "badge badge-cyan";

    triggerTopologyPulse();

    const payload = {
      condition: document.getElementById("filter-condition").value || null,
      severity: document.getElementById("filter-severity").value || null,
      biomarker: document.getElementById("filter-biomarker").value || null,
      abnormal_lab_only: document.getElementById("filter-abnormal").value === "true",
      medication: document.getElementById("filter-medication").value || null,
      response_outcome: document.getElementById("filter-outcome").value || null,
      epsilon: parseFloat(sliderEpsilon.value),
      use_dp: toggleDp.checked,
      use_smpc: toggleSmpc.checked,
      enforce_suppression: toggleSuppression.checked,
      role: roleSelect.value,
      purpose: purposeSelect.value,
      researcher_name: "Dr. Clinical Investigator"
    };

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!data.success) {
        handleQueryError(data);
      } else {
        renderResults(data);
        await fetchAuditBlocks();
      }
    } catch (err) {
      alert("Network or server error while executing query: " + err.message);
      queryStatusBadge.innerText = "Error";
      queryStatusBadge.className = "badge badge-rose";
    } finally {
      btnRunQuery.disabled = false;
      btnRunQuery.innerHTML = `<span class="btn-icon">⚡</span> Run Collaborative Query`;
    }
  });

  function handleQueryError(data) {
    resultsPlaceholder.classList.remove("hidden");
    resultsContent.classList.add("hidden");

    queryStatusBadge.innerText = data.error_type || "Rejected";
    queryStatusBadge.className = "badge badge-rose";

    if (data.error_type === "ACCESS_DENIED") {
      alert(`⚠️ Access Denied (PBAC Policy Enforcement):\n\n${data.error}\n\nTip: Adjust your Role or Declared Purpose in the top header.`);
    } else if (data.error_type === "BUDGET_EXHAUSTED") {
      alert(`⚠️ Privacy Budget Exhausted:\n\n${data.error}\n\nClick "Reset ε" in the header to restart your research session.`);
    } else if (data.error_type === "COHORT_SUPPRESSED") {
      alert(`⚠️ Cell Suppression (HIPAA Safe Harbor Rule):\n\n${data.error}\n\nQueries matching fewer than 5 patients are blocked to prevent individual re-identification.`);
    } else {
      alert(`Query Error: ${data.error}`);
    }

    if (data.budget_status) {
      updateBudgetUI(data.budget_status);
    }
  }

  function renderResults(data) {
    resultsPlaceholder.classList.add("hidden");
    resultsContent.classList.remove("hidden");

    queryStatusBadge.innerText = "Success (Privacy-Preserved)";
    queryStatusBadge.className = "badge badge-emerald";

    const res = data.result;
    const dp = res.differential_privacy;
    const smpc = res.smpc;

    // Primary Metric
    document.getElementById("metric-reported-count").innerText = 
      dp ? dp.perturbed_value.toFixed(1) : res.reported_count;

    if (dp && dp.confidence_interval_95) {
      document.getElementById("metric-ci").innerText = 
        `95% Confidence Interval: [ ${dp.confidence_interval_95.lower} , ${dp.confidence_interval_95.upper} ] (±${dp.confidence_interval_95.margin})`;
    } else {
      document.getElementById("metric-ci").innerText = "Differential Privacy Disabled (Raw Count)";
    }

    // Grid Metrics
    document.getElementById("metric-true-count").innerText = res.true_count;
    document.getElementById("metric-noise-added").innerText = dp ? (dp.noise_added > 0 ? `+${dp.noise_added}` : `${dp.noise_added}`) : "0.0";
    document.getElementById("metric-std-err").innerText = dp ? dp.std_dev.toFixed(2) : "0.0";
    document.getElementById("metric-epsilon-spent").innerText = dp ? `ε = ${dp.epsilon.toFixed(2)}` : "0.0 (DP Off)";
    document.getElementById("metric-budget-left").innerText = `Remaining: ${data.budget_status.remaining_budget.toFixed(2)} ε`;

    // Sieve Steps
    document.getElementById("sieve-a").innerText = res.node_evaluations.hospital_a_matched;
    document.getElementById("sieve-b").innerText = res.node_evaluations.hospital_b_filtered;
    document.getElementById("sieve-c").innerText = res.node_evaluations.hospital_c_final;

    // SMPC Trace
    const smpcBox = document.getElementById("smpc-trace-box");
    const smpcSteps = document.getElementById("smpc-steps");
    smpcSteps.innerHTML = "";

    if (smpc && smpc.protocol_trace) {
      smpcBox.classList.remove("hidden");
      smpc.protocol_trace.forEach(item => {
        const div = document.createElement("div");
        div.className = "trace-step-item";
        div.innerHTML = `
          <div class="trace-step-title">${item.step}</div>
          <div class="trace-step-detail">${item.detail}</div>
        `;
        smpcSteps.appendChild(div);
      });
    } else {
      smpcBox.classList.add("hidden");
    }

    // Audit Info
    document.getElementById("res-audit-index").innerText = data.audit_entry.block_index;
    document.getElementById("res-audit-hash").innerText = data.audit_entry.block_hash.substring(0, 24) + "...";

    // Update Budget
    updateBudgetUI(data.budget_status);
  }

  // ==========================================
  // 6. Hospital Vault Viewer
  // ==========================================
  vaultTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      vaultTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      loadVault(tab.dataset.node);
    });
  });

  async function loadVault(nodeId) {
    try {
      const res = await fetch(`/api/vault/${nodeId}?limit=12`);
      const data = await res.json();
      if (!data.success) return;

      vaultBody.innerHTML = "";
      if (nodeId === "node_a") {
        vaultHeaders.innerHTML = `<th>Token</th><th>Age</th><th>Gender</th><th>Condition</th><th>Severity</th>`;
        data.records.forEach(r => {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td><code>${r.token}</code></td><td>${r.age}</td><td>${r.gender}</td><td>${r.condition}</td><td>${r.severity}</td>`;
          vaultBody.appendChild(tr);
        });
      } else if (nodeId === "node_b") {
        vaultHeaders.innerHTML = `<th>Token</th><th>Biomarker</th><th>Value</th><th>Unit</th><th>Abnormal</th>`;
        data.records.forEach(r => {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td><code>${r.token}</code></td><td>${r.biomarker_name}</td><td>${r.biomarker_value}</td><td>${r.unit}</td><td>${r.abnormal_flag ? '⚠️ Yes' : 'Normal'}</td>`;
          vaultBody.appendChild(tr);
        });
      } else if (nodeId === "node_c") {
        vaultHeaders.innerHTML = `<th>Token</th><th>Medication</th><th>Dosage</th><th>Adherence</th><th>Response</th>`;
        data.records.forEach(r => {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td><code>${r.token}</code></td><td>${r.medication}</td><td>${r.dosage}</td><td>${Math.round(r.adherence_rate * 100)}%</td><td>${r.response_outcome}</td>`;
          vaultBody.appendChild(tr);
        });
      }
    } catch (err) {
      console.error("Failed to load vault records:", err);
    }
  }

  // ==========================================
  // 7. k-Anonymity Exporter
  // ==========================================
  btnExportAnon.addEventListener("click", async () => {
    btnExportAnon.disabled = true;
    btnExportAnon.innerText = "Synthesizing Equivalence Classes...";

    const payload = {
      condition: anonCondition.value,
      k: parseInt(anonK.value, 10),
      l: parseInt(anonL.value, 10),
      role: roleSelect.value,
      purpose: purposeSelect.value
    };

    try {
      const res = await fetch("/api/anonymize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!data.success) {
        alert("Anonymization Export Failed: " + data.error);
      } else {
        renderAnonymizedData(data);
        await fetchAuditBlocks();
      }
    } catch (err) {
      alert("Error generating anonymized dataset: " + err.message);
    } finally {
      btnExportAnon.disabled = false;
      btnExportAnon.innerText = "Generate Anonymized Dataset";
    }
  });

  function renderAnonymizedData(data) {
    anonResults.classList.remove("hidden");
    const summary = data.anonymization_summary;

    anonTotalIn.innerText = summary.total_input_records;
    anonRetained.innerText = summary.retained_records;
    anonSuppressed.innerText = `${summary.suppressed_records} (${summary.suppression_rate_percent}%)`;

    anonTbody.innerHTML = "";
    data.sample_records.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="badge badge-purple">${r.age_group}</span></td>
        <td>${r.gender}</td>
        <td>${r.condition}</td>
        <td>${r.severity}</td>
        <td><strong>${r.outcome}</strong></td>
      `;
      anonTbody.appendChild(tr);
    });
  }

  // ==========================================
  // 8. Cryptographic Audit Ledger
  // ==========================================
  async function fetchAuditBlocks() {
    try {
      const res = await fetch("/api/audit");
      const data = await res.json();
      if (!data.success) return;

      blocksContainer.innerHTML = "";
      data.blocks.slice().reverse().forEach(b => {
        const div = document.createElement("div");
        div.className = "audit-block-card";
        div.id = `block-${b.index}`;
        div.innerHTML = `
          <div class="block-header">
            <span>Block #${b.index} • ${b.query_type}</span>
            <span class="block-time">${new Date(b.timestamp).toLocaleTimeString()}</span>
          </div>
          <div class="block-meta">
            👤 <strong>${b.researcher}</strong> (${b.role}) | 🎯 ${b.purpose} | ε: ${b.epsilon_spent}
          </div>
          <div class="block-hash">Hash: ${b.block_hash}</div>
          <div class="block-prev-hash">Prev: ${b.previous_hash.substring(0, 24)}...</div>
        `;
        blocksContainer.appendChild(div);
      });
    } catch (err) {
      console.error("Failed to fetch audit blocks:", err);
    }
  }

  btnVerifyChain.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/audit/verify", { method: "POST" });
      const data = await res.json();
      if (data.success && data.status.valid) {
        chainIntegrityBadge.innerText = `Chain Valid (${data.status.total_blocks} Blocks)`;
        chainIntegrityBadge.className = "chain-badge valid";
        document.getElementById("ledger-pill").className = "node-pill ledger-ok";
        document.getElementById("ledger-status-text").innerText = "Cryptographically Verified";
        alert("✅ Cryptographic Verification Passed:\nAll SHA-256 block hashes and chaining pointers are untampered.");
      } else {
        chainIntegrityBadge.innerText = `⚠️ Compromised (Block #${data.status.corrupted_block_index})`;
        chainIntegrityBadge.className = "chain-badge tampered";
        document.getElementById("ledger-pill").className = "node-pill";
        document.getElementById("ledger-status-text").innerText = "⚠️ INTEGRITY BREACH DETECTED";
        alert(`🚨 AUDIT INTEGRITY ALERT:\n\n${data.status.reason}\n\nThe cryptographic hash chain has detected unauthorized retroactive tampering!`);
      }
    } catch (err) {
      console.error("Error verifying audit chain:", err);
    }
  });

  btnSimulateTamper.addEventListener("click", async () => {
    try {
      // Tamper with Block #1
      const res = await fetch("/api/audit/tamper", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ block_index: 1, fake_researcher: "MALICIOUS_INSIDER" })
      });
      const data = await res.json();
      if (data.success) {
        btnRestoreChain.classList.remove("hidden");
        btnRestoreChain.dataset.orig = data.original_field;
        await fetchAuditBlocks();
        // Immediately run verify to demonstrate detection
        btnVerifyChain.click();
      }
    } catch (err) {
      console.error("Tamper simulation error:", err);
    }
  });

  btnRestoreChain.addEventListener("click", async () => {
    try {
      const orig = btnRestoreChain.dataset.orig || "Dr. Clinical Investigator";
      const res = await fetch("/api/audit/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ block_index: 1, original_researcher: orig })
      });
      const data = await res.json();
      if (data.success) {
        btnRestoreChain.classList.add("hidden");
        await fetchAuditBlocks();
        btnVerifyChain.click();
      }
    } catch (err) {
      console.error("Restore block error:", err);
    }
  });

  // Start initialization
  init();
});
