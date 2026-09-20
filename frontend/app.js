/**
 * PP-HDB: Multi-Hospital Privacy-Preserving Healthcare System
 * Frontend Controller & Interaction Engine
 */

// Global State
let currentHospitalId = "node_a";
let currentHospitalName = "Hospital A";
let currentAdminName = "Dr. Arthur Vance (CMO)";
let activeTab = "tab-local-ehr";

const HOSPITAL_PROFILES = {
  "node_a": { name: "Hospital A", admin: "Dr. Arthur Vance (CMO)", color: "#3b82f6" },
  "node_b": { name: "Hospital B", admin: "Dr. Beatrice Ramos (Clinical Dir)", color: "#10b981" },
  "node_c": { name: "Hospital C", admin: "Dr. Charles Kim (Pharmacy Head)", color: "#8b5cf6" }
};

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const hospitalSwitch = document.getElementById("hospital-switch-select");
  const activeHospName = document.getElementById("active-hospital-name");
  const activeAdmName = document.getElementById("active-admin-name");
  const hospDot = document.getElementById("hospital-indicator-dot");

  const btnNotifBell = document.getElementById("btn-notif-bell");
  const notifMenu = document.getElementById("notif-menu");
  const notifBadge = document.getElementById("notif-badge");
  const notifList = document.getElementById("notif-list");
  const btnMarkNotifsRead = document.getElementById("btn-mark-notifs-read");

  const navTabs = document.querySelectorAll(".nav-tab");
  const tabContents = document.querySelectorAll(".tab-content");

  // Local EHR Elements
  const localSearch = document.getElementById("local-patient-search");
  const localPatientsTbody = document.getElementById("local-patients-tbody");
  const localEhrTitle = document.getElementById("local-ehr-title");
  const profilePlaceholder = document.getElementById("profile-placeholder");
  const profileContent = document.getElementById("profile-content");

  // Discovery Elements
  const discoveryInput = document.getElementById("discovery-input");
  const btnRunDiscovery = document.getElementById("btn-run-discovery");
  const discoveryResultsWrapper = document.getElementById("discovery-results-wrapper");
  const presenceGrid = document.getElementById("presence-grid");
  const presenceOverallBadge = document.getElementById("presence-overall-badge");
  const requestActionCard = document.getElementById("request-action-card");
  const shareRequestForm = document.getElementById("share-request-form");
  const sharedDataCard = document.getElementById("shared-data-card");
  const sharedPayloadView = document.getElementById("shared-payload-view");

  // Add Patient & Encounter Elements
  const formRegisterPatient = document.getElementById("form-register-patient");
  const formAddEncounter = document.getElementById("form-add-encounter");
  const encTokenSelect = document.getElementById("enc-token-select");
  const encCategory = document.getElementById("enc-category");
  const encDiagFields = document.getElementById("enc-diag-fields");
  const encHistoryFields = document.getElementById("enc-history-fields");
  const encRxFields = document.getElementById("enc-rx-fields");

  // Requests Elements
  const incomingList = document.getElementById("incoming-requests-list");
  const outgoingList = document.getElementById("outgoing-requests-list");
  const incomingBadge = document.getElementById("incoming-count-badge");
  const tabRequestBadge = document.getElementById("tab-request-badge");

  // Dialogs
  const loginDialog = document.getElementById("login-dialog");
  const btnOpenLogin = document.getElementById("btn-open-login");
  const btnCloseLogin = document.getElementById("btn-close-login");
  const loginForm = document.getElementById("login-form");

  const reviewDialog = document.getElementById("review-dialog");
  const btnCloseReview = document.getElementById("btn-close-review");
  const reviewModalBody = document.getElementById("review-modal-body");

  // Analytics
  const analyticsForm = document.getElementById("analytics-query-form");
  const statResultBox = document.getElementById("stat-result-box");
  const statResultBadge = document.getElementById("stat-result-badge");

  // =========================================================================
  // 1. Initialization
  // =========================================================================
  async function init() {
    updateHospitalContext(currentHospitalId);
    setupEventListeners();
    await refreshAllData();
    // Poll notifications every 8 seconds
    setInterval(fetchNotifications, 8000);
  }

  function updateHospitalContext(hId) {
    currentHospitalId = hId;
    const info = HOSPITAL_PROFILES[hId];
    currentHospitalName = info.name;
    currentAdminName = info.admin;

    activeHospName.innerText = info.name;
    activeAdmName.innerText = info.admin;
    hospDot.style.background = info.color;
    hospDot.style.boxShadow = `0 0 10px ${info.color}`;

    localEhrTitle.innerText = `${info.name}: Local Patient Roster`;
    document.getElementById("add-patient-hospital-badge").innerText = info.name;
    hospitalSwitch.value = hId;
  }

  async function refreshAllData() {
    await fetchLocalPatients();
    await fetchNotifications();
    await fetchSharingRequests();
  }

  // =========================================================================
  // 2. Navigation Tabs
  // =========================================================================
  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      navTabs.forEach(t => t.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      activeTab = tab.dataset.tab;
      document.getElementById(activeTab).classList.add("active");

      if (activeTab === "tab-local-ehr") fetchLocalPatients();
      if (activeTab === "tab-sharing-requests") fetchSharingRequests();
    });
  });

  // =========================================================================
  // 3. Hospital Switcher & Authentication
  // =========================================================================
  hospitalSwitch.addEventListener("change", (e) => {
    updateHospitalContext(e.target.value);
    profileContent.classList.add("hidden");
    profilePlaceholder.classList.remove("hidden");
    discoveryResultsWrapper.classList.add("hidden");
    refreshAllData();
  });

  btnOpenLogin.addEventListener("click", () => loginDialog.showModal());
  btnCloseLogin.addEventListener("click", () => loginDialog.close());

  window.selectLogin = function(username) {
    document.getElementById("login-username").value = username;
  };

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const u = document.getElementById("login-username").value;
    const p = document.getElementById("login-password").value;

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await res.json();
      if (data.success) {
        updateHospitalContext(data.user.hospital_id);
        loginDialog.close();
        refreshAllData();
      } else {
        alert("Login failed: " + data.error);
      }
    } catch (err) {
      alert("Error signing in: " + err.message);
    }
  });

  // =========================================================================
  // 4. Notifications Popover
  // =========================================================================
  btnNotifBell.addEventListener("click", (e) => {
    e.stopPropagation();
    notifMenu.classList.toggle("hidden");
  });

  document.addEventListener("click", (e) => {
    if (!notifMenu.contains(e.target) && e.target !== btnNotifBell) {
      notifMenu.classList.add("hidden");
    }
  });

  async function fetchNotifications() {
    try {
      const res = await fetch(`/api/notifications?hospital_id=${currentHospitalId}`);
      const data = await res.json();
      if (!data.success) return;

      const notifs = data.notifications;
      const unread = data.unread_count;

      if (unread > 0) {
        notifBadge.innerText = unread;
        notifBadge.classList.remove("hidden");
      } else {
        notifBadge.classList.add("hidden");
      }

      if (notifs.length === 0) {
        notifList.innerHTML = `<div class="notif-empty">No notifications for ${currentHospitalName}</div>`;
      } else {
        notifList.innerHTML = "";
        notifs.forEach(n => {
          const div = document.createElement("div");
          div.className = `notif-item ${n.is_read ? '' : 'unread'}`;
          div.innerHTML = `
            <div class="notif-title">${n.title}</div>
            <div class="notif-body">${n.message}</div>
            <div class="notif-time">${new Date(n.created_at).toLocaleTimeString()} • ${n.request_id}</div>
          `;
          div.addEventListener("click", () => {
            notifMenu.classList.add("hidden");
            // Jump to requests tab
            const reqTabBtn = document.querySelector('[data-tab="tab-sharing-requests"]');
            if (reqTabBtn) reqTabBtn.click();
          });
          notifList.appendChild(div);
        });
      }
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
    }
  }

  btnMarkNotifsRead.addEventListener("click", async () => {
    try {
      await fetch("/api/notifications/mark-read", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hospital_id: currentHospitalId })
      });
      fetchNotifications();
    } catch (err) {
      console.error(err);
    }
  });

  // =========================================================================
  // 5. Local Patient Records (EHR)
  // =========================================================================
  async function fetchLocalPatients() {
    try {
      const q = localSearch.value || "";
      const res = await fetch(`/api/patient/search?hospital_id=${currentHospitalId}&q=${encodeURIComponent(q)}`);
      const data = await res.json();
      if (!data.success) return;

      localPatientsTbody.innerHTML = "";
      encTokenSelect.innerHTML = "";

      if (data.patients.length === 0) {
        localPatientsTbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-muted);">No patients found in local database.</td></tr>`;
        return;
      }

      data.patients.forEach(p => {
        // Add to local roster table
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${p.name}</strong><br><code style="font-size:0.68rem; color:var(--text-muted);">${p.token.substring(0, 14)}...</code></td>
          <td>${p.age} / ${p.gender}</td>
          <td><span class="badge badge-cyan">${p.blood_group}</span></td>
          <td>${p.primary_condition}</td>
          <td><span class="badge badge-emerald">Available</span></td>
          <td><button class="btn-xs" onclick="viewLocalChart('${p.token}')">View Chart</button></td>
        `;
        localPatientsTbody.appendChild(tr);

        // Populate Add Encounter select
        const opt = document.createElement("option");
        opt.value = p.token;
        opt.innerText = `${p.name} (${p.primary_condition})`;
        encTokenSelect.appendChild(opt);
      });
    } catch (err) {
      console.error("Error fetching local patients:", err);
    }
  }

  localSearch.addEventListener("input", debounce(fetchLocalPatients, 300));

  window.viewLocalChart = async function(token) {
    try {
      const res = await fetch(`/api/patient/profile?hospital_id=${currentHospitalId}&token=${token}`);
      const data = await res.json();
      if (!data.success) return;

      const p = data.profile.patient;
      const history = data.profile.medical_history;
      const diagnostics = data.profile.diagnostics;
      const prescriptions = data.profile.prescriptions;

      profilePlaceholder.classList.add("hidden");
      profileContent.classList.remove("hidden");

      document.getElementById("profile-token-badge").innerText = token.substring(0, 16);
      document.getElementById("prof-name").innerText = p.name;
      document.getElementById("prof-meta").innerText = `${p.age} yrs • ${p.gender === 'M' ? 'Male' : 'Female'} • Blood: ${p.blood_group} • Allergies: ${p.allergies}`;
      document.getElementById("prof-condition-tag").innerText = p.primary_condition;

      // History
      const hList = document.getElementById("prof-history-list");
      hList.innerHTML = history.length ? "" : "<div class='placeholder-msg'>No prior diagnoses recorded locally.</div>";
      history.forEach(h => {
        hList.innerHTML += `
          <div class="chart-item">
            <div class="chart-item-main">
              <strong>${h.condition}</strong> (${h.icd10}) • <em>${h.severity}</em>
              <div class="chart-item-meta">${h.clinical_notes}</div>
            </div>
            <span class="badge badge-purple">${h.diagnosis_year}</span>
          </div>
        `;
      });

      // Diagnostics
      const dList = document.getElementById("prof-diag-list");
      dList.innerHTML = diagnostics.length ? "" : "<div class='placeholder-msg'>No diagnostic reports recorded locally.</div>";
      diagnostics.forEach(d => {
        dList.innerHTML += `
          <div class="chart-item">
            <div class="chart-item-main">
              <strong>${d.biomarker_name}</strong>: ${d.biomarker_value} ${d.unit}
              <div class="chart-item-meta">${d.test_name}</div>
            </div>
            <span class="badge ${d.abnormal_flag ? 'badge-rose' : 'badge-emerald'}">
              ${d.abnormal_flag ? '⚠️ Abnormal' : 'Normal'} (${d.test_year})
            </span>
          </div>
        `;
      });

      // Prescriptions
      const rList = document.getElementById("prof-rx-list");
      rList.innerHTML = prescriptions.length ? "" : "<div class='placeholder-msg'>No active prescriptions recorded locally.</div>";
      prescriptions.forEach(r => {
        rList.innerHTML += `
          <div class="chart-item">
            <div class="chart-item-main">
              <strong>${r.medication}</strong> (${r.dosage}) • ${r.frequency}
              <div class="chart-item-meta">Adherence: ${Math.round(r.adherence_rate * 100)}%</div>
            </div>
            <span class="badge badge-cyan">${r.response_outcome}</span>
          </div>
        `;
      });

    } catch (err) {
      console.error("Error viewing patient chart:", err);
    }
  };

  // =========================================================================
  // 6. Patient Discovery & Presence Locator
  // =========================================================================
  btnRunDiscovery.addEventListener("click", runDiscoverySearch);
  discoveryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runDiscoverySearch();
  });

  // Quick Chips
  document.querySelectorAll(".chip-btn").forEach(chip => {
    chip.addEventListener("click", () => {
      discoveryInput.value = chip.dataset.query;
      runDiscoverySearch();
    });
  });

  async function runDiscoverySearch() {
    const q = discoveryInput.value.trim();
    if (!q) return;

    btnRunDiscovery.disabled = true;
    btnRunDiscovery.innerText = "Checking Federation Nodes...";

    try {
      const res = await fetch(`/api/patient/discover?hospital_id=${currentHospitalId}&q=${encodeURIComponent(q)}`);
      const data = await res.json();

      if (!data.success) {
        alert(data.error);
        return;
      }

      renderDiscoveryResults(data.discovery);
    } catch (err) {
      alert("Discovery error: " + err.message);
    } finally {
      btnRunDiscovery.disabled = false;
      btnRunDiscovery.innerText = "🔍 Check Data Availability Across Federation";
    }
  }

  function renderDiscoveryResults(discovery) {
    discoveryResultsWrapper.classList.remove("hidden");
    requestActionCard.classList.add("hidden");
    sharedDataCard.classList.add("hidden");

    if (!discovery.found_anywhere) {
      presenceOverallBadge.innerText = "NOT PRESENT ANYWHERE IN FEDERATION";
      presenceOverallBadge.className = "badge badge-rose";
      presenceGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 2.5rem; text-align: center; background: rgba(0,0,0,0.3); border-radius: var(--radius-lg);">
          <h3 style="color: var(--accent-rose);">❌ No Records Found</h3>
          <p style="color: var(--text-secondary); margin-top: 0.5rem;">
            Patient "${discovery.search_query}" is not registered in Hospital A, Hospital B, or Hospital C.
          </p>
        </div>
      `;
      return;
    }

    presenceOverallBadge.innerText = "PATIENT LOCATED IN FEDERATION";
    presenceOverallBadge.className = "badge badge-emerald";

    presenceGrid.innerHTML = "";
    discovery.federation_presence.forEach(node => {
      const isCurrent = node.is_current_hospital;
      const isPresent = node.present;

      const div = document.createElement("div");
      div.className = `presence-card ${isCurrent ? 'current' : ''} ${isPresent ? 'available' : ''}`;

      let actionHtml = "";
      if (isCurrent && isPresent) {
        actionHtml = `<span class="badge badge-cyan">Data Present in Local Vault</span>`;
      } else if (!isCurrent && isPresent) {
        actionHtml = `
          <button class="btn-xs success" onclick="openRequestForm('${node.hospital_id}', '${node.hospital_name}', '${discovery.patient_token}', '${discovery.patient_name || 'Patient'}')">
            Request Scoped Data from ${node.hospital_name}
          </button>
        `;
      } else {
        actionHtml = `<span class="badge badge-rose">No Records at this site</span>`;
      }

      div.innerHTML = `
        <div class="presence-header">
          <span class="presence-hname">${node.hospital_name} ${isCurrent ? '(This Hospital)' : ''}</span>
          <span class="presence-status-badge ${isPresent ? 'status-present' : 'status-absent'}">
            ${isPresent ? '● PRESENT' : '○ ABSENT'}
          </span>
        </div>

        <div class="category-tags">
          <div class="cat-indicator ${node.categories.medical_history ? 'has' : 'nohas'}">
            ${node.categories.medical_history ? '✓' : '✗'} Medical History & ICD-10
          </div>
          <div class="cat-indicator ${node.categories.diagnostics ? 'has' : 'nohas'}">
            ${node.categories.diagnostics ? '✓' : '✗'} Diagnostic Reports & Labs
          </div>
          <div class="cat-indicator ${node.categories.prescriptions ? 'has' : 'nohas'}">
            ${node.categories.prescriptions ? '✓' : '✗'} Prescriptions & Pharmacy
          </div>
        </div>

        <div style="margin-top: 0.5rem; border-top: 1px solid var(--border-color); padding-top: 0.5rem;">
          ${actionHtml}
        </div>
      `;
      presenceGrid.appendChild(div);
    });
  }

  window.openRequestForm = function(targetHospId, targetHospName, token, pName) {
    requestActionCard.classList.remove("hidden");
    document.getElementById("req-target-hospital-id").value = targetHospId;
    document.getElementById("req-target-hospital-name").value = `${targetHospName} (${targetHospId.toUpperCase()})`;
    document.getElementById("req-patient-token").value = token;
    document.getElementById("req-patient-name").value = pName;

    requestActionCard.scrollIntoView({ behavior: "smooth" });
  };

  shareRequestForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const targetHospId = document.getElementById("req-target-hospital-id").value;
    const token = document.getElementById("req-patient-token").value;
    const pName = document.getElementById("req-patient-name").value;
    const purpose = document.getElementById("req-purpose").value;
    const justification = document.getElementById("req-justification").value;

    const categories = [];
    if (document.getElementById("req-cat-history").checked) categories.push("medical_history");
    if (document.getElementById("req-cat-diagnostics").checked) categories.push("diagnostics");
    if (document.getElementById("req-cat-prescriptions").checked) categories.push("prescriptions");

    if (categories.length === 0) {
      alert("Please select at least one data category to request.");
      return;
    }

    try {
      const res = await fetch("/api/sharing/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_hospital: currentHospitalId,
          to_hospital: targetHospId,
          patient_token: token,
          patient_name: pName,
          requested_categories: categories,
          purpose: purpose,
          justification: justification
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ Request Submitted!\n\n${data.message}\n\nTarget Hospital Admin has been notified to review and verify this request.`);
        requestActionCard.classList.add("hidden");
        fetchSharingRequests();
      } else {
        alert("Request failed: " + data.error);
      }
    } catch (err) {
      alert("Error submitting request: " + err.message);
    }
  });

  // =========================================================================
  // 7. Sharing Requests & Review Workflow
  // =========================================================================
  async function fetchSharingRequests() {
    try {
      const res = await fetch(`/api/sharing/requests?hospital_id=${currentHospitalId}`);
      const data = await res.json();
      if (!data.success) return;

      const incoming = data.requests.incoming;
      const outgoing = data.requests.outgoing;

      const pendingIncoming = incoming.filter(r => r.status === "PENDING").length;
      incomingBadge.innerText = `${pendingIncoming} Pending`;
      if (pendingIncoming > 0) {
        tabRequestBadge.innerText = pendingIncoming;
        tabRequestBadge.classList.remove("hidden");
      } else {
        tabRequestBadge.classList.add("hidden");
      }

      // Render Incoming
      incomingList.innerHTML = incoming.length ? "" : "<div class='placeholder-msg'>No incoming data requests.</div>";
      incoming.forEach(r => {
        const cats = JSON.parse(r.requested_categories).map(c => c.replace("_", " ")).join(", ");
        const card = document.createElement("div");
        card.className = "request-card";
        card.innerHTML = `
          <div class="request-card-header">
            <span class="req-id">${r.request_id} • From ${r.from_hospital.toUpperCase()}</span>
            <span class="req-status-badge status-${r.status.toLowerCase()}">${r.status}</span>
          </div>
          <div>
            <strong>Patient:</strong> ${r.patient_name} (<code style="font-size:0.68rem;">${r.patient_token.substring(0, 12)}...</code>)<br>
            <strong>Requested Categories:</strong> <span style="color:var(--accent-cyan); font-weight:600;">[${cats}]</span><br>
            <strong>Declared Purpose:</strong> ${r.purpose}<br>
            <em style="color:var(--text-muted); font-size:0.75rem;">"${r.justification}"</em>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.3rem;">
            <span style="font-size:0.68rem; color:var(--text-muted);">${new Date(r.created_at).toLocaleString()}</span>
            ${r.status === 'PENDING' ? `<button class="btn-xs success" onclick="openReviewModal('${r.request_id}')">Review & Verify</button>` : `<span style="font-size:0.72rem; color:var(--text-muted);">Reviewed by ${r.reviewer || 'Admin'}</span>`}
          </div>
        `;
        incomingList.appendChild(card);
      });

      // Render Outgoing
      outgoingList.innerHTML = outgoing.length ? "" : "<div class='placeholder-msg'>No outgoing data requests.</div>";
      outgoing.forEach(r => {
        const cats = JSON.parse(r.requested_categories).map(c => c.replace("_", " ")).join(", ");
        const card = document.createElement("div");
        card.className = "request-card";
        card.innerHTML = `
          <div class="request-card-header">
            <span class="req-id">${r.request_id} • To ${r.to_hospital.toUpperCase()}</span>
            <span class="req-status-badge status-${r.status.toLowerCase()}">${r.status}</span>
          </div>
          <div>
            <strong>Patient:</strong> ${r.patient_name}<br>
            <strong>Requested Data:</strong> [${cats}]<br>
            <strong>Purpose:</strong> ${r.purpose}
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.3rem;">
            <span style="font-size:0.68rem; color:var(--text-muted);">${new Date(r.created_at).toLocaleString()}</span>
            ${r.status === 'APPROVED' ? `<button class="btn-xs" onclick="viewSharedPayload('${r.request_id}')">View Verified Payload</button>` : ''}
          </div>
        `;
        outgoingList.appendChild(card);
      });

    } catch (err) {
      console.error("Error fetching sharing requests:", err);
    }
  }

  window.openReviewModal = async function(requestId) {
    const res = await fetch(`/api/sharing/requests?hospital_id=${currentHospitalId}`);
    const data = await res.json();
    const req = data.requests.incoming.find(r => r.request_id === requestId);
    if (!req) return;

    const reqCats = JSON.parse(req.requested_categories);

    reviewModalBody.innerHTML = `
      <div style="margin-bottom:1rem;">
        <strong>Requesting Entity:</strong> ${req.from_hospital.toUpperCase()} Clinician<br>
        <strong>Target Patient:</strong> ${req.patient_name} (${req.patient_token.substring(0, 14)}...)<br>
        <strong>Stated Purpose:</strong> ${req.purpose}<br>
        <strong>Justification:</strong> <em>"${req.justification}"</em>
      </div>

      <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:0.85rem; margin-bottom:1.25rem;">
        <h4 style="font-size:0.8rem; margin-bottom:0.5rem; color:var(--accent-cyan);">Granular Authorization (Data Minimization):</h4>
        <p style="font-size:0.72rem; color:var(--text-secondary); margin-bottom:0.5rem;">Uncheck any categories you wish to redact from the shared payload:</p>
        
        <label class="checkbox-pill" style="margin-bottom:0.4rem;">
          <input type="checkbox" id="rev-cat-history" ${reqCats.includes('medical_history') ? 'checked' : 'disabled'}>
          <span>🩺 Patient Medical History</span>
        </label>
        <label class="checkbox-pill" style="margin-bottom:0.4rem;">
          <input type="checkbox" id="rev-cat-diagnostics" ${reqCats.includes('diagnostics') ? 'checked' : 'disabled'}>
          <span>🔬 Diagnostic Lab Reports</span>
        </label>
        <label class="checkbox-pill">
          <input type="checkbox" id="rev-cat-prescriptions" ${reqCats.includes('prescriptions') ? 'checked' : 'disabled'}>
          <span>💊 Active Prescriptions</span>
        </label>
      </div>

      <div style="display:flex; gap:0.75rem; justify-content:flex-end;">
        <button class="btn-xs danger" onclick="submitReviewDecision('${requestId}', 'REJECTED')">Decline Request</button>
        <button class="btn-primary" onclick="submitReviewDecision('${requestId}', 'APPROVED')">Verify & Approve Scoped Release</button>
      </div>
    `;

    reviewDialog.showModal();
  };

  btnCloseReview.addEventListener("click", () => reviewDialog.close());

  window.submitReviewDecision = async function(requestId, decision) {
    const approvedCats = [];
    if (decision === "APPROVED") {
      if (document.getElementById("rev-cat-history")?.checked) approvedCats.push("medical_history");
      if (document.getElementById("rev-cat-diagnostics")?.checked) approvedCats.push("diagnostics");
      if (document.getElementById("rev-cat-prescriptions")?.checked) approvedCats.push("prescriptions");
      if (approvedCats.length === 0) {
        alert("Please approve at least one category, or click 'Decline Request'.");
        return;
      }
    }

    try {
      const res = await fetch("/api/sharing/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId,
          reviewer_hospital: currentHospitalId,
          reviewer_name: currentAdminName,
          decision: decision,
          approved_categories: approvedCats
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Request ${decision.toLowerCase()} successfully.`);
        reviewDialog.close();
        fetchSharingRequests();
      } else {
        alert("Error: " + data.error);
      }
    } catch (err) {
      alert("Error submitting review: " + err.message);
    }
  };

  window.viewSharedPayload = async function(requestId) {
    const res = await fetch(`/api/sharing/requests?hospital_id=${currentHospitalId}`);
    const data = await res.json();
    const req = data.requests.outgoing.find(r => r.request_id === requestId);
    if (!req || !req.shared_payload) {
      alert("Shared payload not available yet.");
      return;
    }

    const payload = JSON.parse(req.shared_payload);
    sharedDataCard.classList.remove("hidden");
    document.querySelector('[data-tab="tab-discovery"]').click();

    let html = `
      <div style="background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16,185,129,0.3); border-radius:var(--radius-md); padding:0.85rem; margin-bottom:1rem;">
        <strong style="color:var(--accent-emerald);">Verified by ${req.to_hospital.toUpperCase()} Admin (${req.reviewer || 'Doctor'})</strong><br>
        <span style="font-size:0.75rem; color:var(--text-secondary);">Approved Categories: ${req.approved_categories}</span>
      </div>
    `;

    if (payload.medical_history) {
      html += `<h4>🩺 Medical History:</h4>`;
      payload.medical_history.forEach(h => {
        html += `<div class="chart-item"><strong>${h.condition}</strong> (${h.icd10}) • ${h.clinical_notes}</div>`;
      });
    }

    if (payload.diagnostics) {
      html += `<h4 style="margin-top:0.75rem;">🔬 Diagnostic Reports:</h4>`;
      payload.diagnostics.forEach(d => {
        html += `<div class="chart-item"><strong>${d.biomarker_name}</strong>: ${d.biomarker_value} ${d.unit} (${d.abnormal_flag ? '⚠️ Abnormal' : 'Normal'})</div>`;
      });
    }

    if (payload.prescriptions) {
      html += `<h4 style="margin-top:0.75rem;">💊 Prescriptions:</h4>`;
      payload.prescriptions.forEach(p => {
        html += `<div class="chart-item"><strong>${p.medication}</strong> (${p.dosage}) • Outcome: ${p.response_outcome}</div>`;
      });
    }

    sharedPayloadView.innerHTML = html;
    sharedDataCard.scrollIntoView({ behavior: "smooth" });
  };

  // =========================================================================
  // 8. Add Patient & Encounters
  // =========================================================================
  formRegisterPatient.addEventListener("submit", async (e) => {
    e.preventDefault();
    const natId = document.getElementById("new-nat-id").value;
    const name = document.getElementById("new-name").value;
    const age = document.getElementById("new-age").value;
    const gender = document.getElementById("new-gender").value;
    const blood = document.getElementById("new-blood").value;
    const cond = document.getElementById("new-condition").value;
    const allergy = document.getElementById("new-allergies").value;

    try {
      const res = await fetch("/api/patient/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hospital_id: currentHospitalId,
          national_id: natId,
          name: name,
          age: age,
          gender: gender,
          blood_group: blood,
          primary_condition: cond,
          allergies: allergy
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ Patient "${name}" successfully registered in ${currentHospitalName}!\nBlinded Token: ${data.token}`);
        formRegisterPatient.reset();
        fetchLocalPatients();
      } else {
        alert("Error: " + data.error);
      }
    } catch (err) {
      alert("Error adding patient: " + err.message);
    }
  });

  encCategory.addEventListener("change", (e) => {
    encDiagFields.classList.add("hidden");
    encHistoryFields.classList.add("hidden");
    encRxFields.classList.add("hidden");

    if (e.target.value === "diagnostics") encDiagFields.classList.remove("hidden");
    if (e.target.value === "medical_history") encHistoryFields.classList.remove("hidden");
    if (e.target.value === "prescriptions") encRxFields.classList.remove("hidden");
  });

  formAddEncounter.addEventListener("submit", async (e) => {
    e.preventDefault();
    const token = encTokenSelect.value;
    const cat = encCategory.value;

    let payload = {};
    if (cat === "diagnostics") {
      payload = {
        test_name: document.getElementById("enc-diag-name").value,
        biomarker_name: document.getElementById("enc-biomarker").value,
        biomarker_value: document.getElementById("enc-val").value,
        unit: "mg/dL",
        abnormal_flag: document.getElementById("enc-abnormal").value === "1"
      };
    } else if (cat === "medical_history") {
      payload = {
        condition: document.getElementById("enc-cond").value,
        severity: document.getElementById("enc-severity").value,
        clinical_notes: document.getElementById("enc-notes").value
      };
    } else if (cat === "prescriptions") {
      payload = {
        medication: document.getElementById("enc-drug").value,
        dosage: document.getElementById("enc-dose").value,
        frequency: "Daily"
      };
    }

    try {
      const res = await fetch("/api/patient/encounter/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hospital_id: currentHospitalId,
          token: token,
          category: cat,
          encounter_data: payload
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ Clinical encounter recorded in ${currentHospitalName} local vault!`);
        fetchLocalPatients();
      } else {
        alert("Error recording encounter: " + data.error);
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  });

  // =========================================================================
  // 9. Analytics & Statistical Studio
  // =========================================================================
  analyticsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    statResultBadge.innerText = "Querying...";

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          condition: document.getElementById("stat-condition").value,
          medication: document.getElementById("stat-drug").value,
          response_outcome: document.getElementById("stat-outcome").value,
          epsilon: parseFloat(document.getElementById("stat-epsilon").value),
          use_dp: true,
          use_smpc: true
        })
      });
      const data = await res.json();
      if (data.success) {
        statResultBadge.innerText = "Complete";
        const r = data.result;
        statResultBox.innerHTML = `
          <div style="font-size:2rem; font-weight:800; color:var(--accent-cyan);">${r.reported_count} Patients</div>
          <div style="font-family:var(--font-mono); font-size:0.8rem; color:var(--text-secondary);">
            True Count: ${r.true_count} • Noise: ${r.differential_privacy.noise_added} • ε = ${r.differential_privacy.epsilon}
          </div>
          <div style="font-family:var(--font-mono); font-size:0.75rem; color:var(--accent-emerald); margin-top:0.3rem;">
            95% CI: [ ${r.differential_privacy.confidence_interval_95.lower} , ${r.differential_privacy.confidence_interval_95.upper} ]
          </div>
        `;
      }
    } catch (err) {
      console.error(err);
    }
  });

  // Helper
  function debounce(fn, delay) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn(...args), delay);
    };
  }

  function setupEventListeners() {}

  // Run initialization
  init();
});
