# PP-HDB: Multi-Hospital Privacy-Preserving Healthcare System

> A federated, full-spectrum multi-hospital database network enabling local electronic health record management, privacy-preserving cross-hospital patient discovery, and granular, verified data sharing between hospital enclaves.

---

## 1. System Overview & Architecture

Modern healthcare requires collaboration across medical centers when patients transition between care providers (e.g. visiting Hospital A first, then Hospital B). Traditional systems either leak all medical records or suffer from complete data blindness.

**PP-HDB solves this with a Defense-in-Depth architecture:**
1. **Full-Spectrum Local Enclaves**: Each hospital (Hospital A, Hospital B, Hospital C) maintains its own full local database storing **Medical History**, **Diagnostic Reports**, and **Prescriptions**.
2. **Zero-Knowledge Patient Discovery Locator**: When a patient visits Hospital B, Hospital B can verify *whether* records exist at peer hospitals without leaking any clinical contents prior to consent.
3. **Granular, Purpose-Bound Sharing Requests**: Hospital B requests *only the specific categories* needed for clinical care (e.g., only Diagnostics or only Medical History).
4. **Target Hospital Review & Verification**: Hospital A's medical administrator receives an instant top-bar notification, reviews the clinical purpose and justification, and verifies which categories/fields to release.
5. **Real-Time Notification System**: Interactive notification bell with unread badge counter and popover menu on the top navigation bar.
6. **Data Minimization Enforcement**: Only verified, approved categories are decrypted and delivered to the requesting hospital.
7. **Tamper-Evident SHA-256 Audit Ledger**: Every discovery lookup, request, review decision, and data transfer is cryptographically sealed into an immutable hash chain.

---

## 2. Walkthrough: The Cross-Visit Scenario

### Scenario:
* Patient **Sarah Jenkins** (`NAT-10001`) visits **Hospital A** first:
  * Hospital A records full clinical history (Type-2 Diabetes, ICD-10: E11.9, severity: Moderate).
  * Hospital A conducts baseline diagnostic lab work (HbA1c: 7.2%).
  * Hospital A prescribes Metformin (1000mg BID).
* Later, Sarah Jenkins visits **Hospital B**:
  1. Hospital B checks its local database: **Record is Missing Locally**.
  2. Hospital B runs the **Federation Discovery Locator**:
     * **Hospital B (Local):** Absent
     * **Hospital A:** Present (Medical History: Yes, Diagnostics: Yes, Prescriptions: Yes)
     * **Hospital C:** Absent
  3. Hospital B initiates a **Scoped Data Request** to Hospital A:
     * Requested categories: `[x] Medical History`, `[x] Diagnostics` (Prescriptions omitted for data minimization).
     * Declared clinical purpose: `Continuation of Care`.
     * Justification: *"Patient presenting for outpatient clinical evaluation."*
  4. Hospital A's administrator receives an instant **Top-Bar Notification**.
  5. Hospital A reviews the request, verifies clinical necessity, and clicks **"Verify & Approve Scoped Access"**.
  6. Hospital B receives notification and views the **Verified Shared Payload**:
     * Contains: `patient_demographics`, `medical_history`, `diagnostics`.
     * Prescriptions are strictly withheld (enforcing data minimization).
  7. Hospital B registers a follow-up diagnostic encounter into its local database.

---

## 3. Hospital Enclaves & Admin Portals

| Hospital Enclave | Domain | Default Admin Login | Password | Enclave Focus |
| :--- | :--- | :--- | :--- | :--- |
| **🏥 Hospital A** | General Medicine & EHR | `admin@hospital-a.org` | `admin123` | Intake, Chronic Care, Demographics |
| **🔬 Hospital B** | Diagnostics & Labs | `admin@hospital-b.org` | `admin123` | Biomarkers, Imaging, Laboratory Panels |
| **💊 Hospital C** | Pharmacy & Therapeutics | `admin@hospital-c.org` | `admin123` | Medications, Adherence, Drug Safety |

*Admins can log in via the authentication modal or use the 1-click enclave switcher on the top navigation bar.*

---

## 4. Web Interface Capabilities

The web application (`http://127.0.0.1:8000`) features:
1. **Top Navigation & Notification Dropdown**:
   - Active hospital badge with real-time health indicator dot.
   - Enclave switcher dropdown.
   - Interactive notification bell with unread badge counter and popover menu.
2. **Local Hospital Records (EHR)**:
   - Browse and filter all patients registered in the active hospital's local vault.
   - Comprehensive Patient Clinical Chart showing demographics, medical history timeline, diagnostic reports, and pharmacy records.
3. **Patient Discovery & Inter-Hospital Exchange**:
   - Search by Patient Name, MRN, or Blinded Token.
   - Real-time **Federation Availability Matrix** showing whether the patient exists in Hospital A, B, or C, or is not present anywhere.
   - Scoped Data Sharing request builder.
   - Verified shared payload viewer with cryptographic provenance badge.
4. **Add Patient Data (Clinical Encounters)**:
   - Form to register new patients into the active local hospital vault.
   - Encounter builder to record new diagnoses, lab reports, or prescriptions.
5. **Sharing Requests & Verification Queue**:
   - Review incoming requests from peer hospitals.
   - Granular authorization modal allowing admins to redact or verify specific categories.
   - Track outgoing request status.
6. **Federated Analytics & DP Studio**:
   - Statistical queries with Differential Privacy ($\epsilon$-slider) and SMPC additive secret sharing.
   - Cryptographic SHA-256 audit ledger with tamper detection.

---

## 5. Testing & Verification

### Run Automated Unit & Integration Tests:
```powershell
python run_tests.py
```
*Executes all 12 test suites verifying Differential Privacy noise scale, Gaussian variance, budget exhaustion, small cohort suppression, secret sharing, multi-party sum, SHA-256 chain verification, tamper detection, PBAC rejection, $k$-anonymity, and the end-to-end inter-hospital discovery & scoped sharing workflow.*

### Run Live Server Verification:
```powershell
python tests/test_live_server.py
```
*Validates all 10 live endpoints on `http://127.0.0.1:8000` including authentication, local search, cross-hospital discovery, scoped request creation, notification delivery, verified review, payload extraction, and encounter additions.*

---

## 6. How to Launch

```powershell
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```
