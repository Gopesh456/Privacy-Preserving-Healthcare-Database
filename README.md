# PP-HDB: Privacy-Preserving Healthcare Database System

> A federated, multi-institution database architecture enabling collaborative clinical research across siloed hospitals without exposing individual patient records.

---

## 1. Problem Statement & Research Formulation

### The Healthcare Data Silo Dilemma
Modern clinical care and medical research are distributed across specialized institutions:
* **Hospital A** holds **Patient Medical History** (clinical diagnoses, ICD-10 condition codes, severity, admission dates).
* **Hospital B** holds **Patient Diagnostic Reports** (biomarkers, lab test results, numeric values, imaging findings).
* **Hospital C** holds **Prescription & Pharmacy Data** (prescribed drugs, dosages, patient adherence, therapeutic response).

Combining these datasets could dramatically improve treatment discovery, personalized medicine, and epidemiologic surveillance. However, medical records represent some of the most sensitive personal data in existence, protected by stringent regulations (HIPAA, GDPR, CCPA).

### The Core Research Question
> *"Can hospitals collaborate and query useful patient information without exposing the patients' private data?"*

**Answer:** **Yes.** Rather than pooling raw patient records into a centralized database or sharing unencrypted identifiable files, PP-HDB employs a **Defense-in-Depth Privacy Pipeline** combining cryptographic entity resolution, Secure Multi-Party Computation (SMPC), Differential Privacy (DP), and tamper-evident audit chaining.

---

## 2. Threat Model & Privacy Defense

| Attack Vector | Threat Scenario | PP-HDB Defense Mechanism |
| :--- | :--- | :--- |
| **Identity Linkage Attack** | Correlating names, SSNs, or quasi-identifiers across hospitals to re-identify patients. | **HMAC-SHA256 Blinded Tokens** / Private Set Intersection (PSI). Plain identifiers never leave the hospital. |
| **Reconstruction / Differencing Attack** | An adversary issues overlapping queries (e.g., $Q_1$: 50 patients, $Q_2$: 49 patients) to isolate 1 patient's record. | **Differential Privacy (Laplace Mechanism)** adds calibrated noise: $\tilde{f} = f + \text{Lap}(1/\epsilon)$, bounded by a **Privacy Budget Accountant ($\epsilon, \delta$)**. |
| **Singling-Out / Small Cohort Attack** | A query matches only 1 or 2 unique patients (e.g. rare disease in a specific age band). | **Cell Suppression Rule**: Queries returning $< 5$ patients are suppressed (HIPAA Safe Harbor guideline). |
| **Intermediate Sub-Count Leakage** | A curious coordinator or peer hospital infers a specific hospital's private sub-count. | **SMPC Additive Secret Sharing**: Each hospital splits counts into shares over field $\mathbb{Z}_M$. Only global sum is reconstructed. |
| **Microdata De-anonymization** | An investigator needs tabular exploratory data rather than a single count. | **$k$-Anonymity ($k \ge 5$) & $\ell$-Diversity ($\ell \ge 2$)**: Quasi-identifiers (Age, Gender) are generalized into intervals and sensitive diversity is enforced. |
| **Unauthorized / Dishonest Queries** | An insider queries sensitive medical data without valid clinical justification. | **Purpose-Based Access Control (PBAC/RBAC)**: Queries require authenticated roles and declared medical purposes. |
| **Audit Log Tampering** | An attacker alters access logs retroactively to hide an illicit query. | **SHA-256 Hash-Chain Audit Ledger**: Every query is logged into an immutable block; tampering invalidates downstream hashes. |

---

## 3. Defense-in-Depth Privacy Architecture

```
                                  [ Researcher / Clinician Query ]
                                                │
                                    [ 1. PBAC / RBAC Gate ]
                             (Role & Purpose Validation + Quota Check)
                                                │
                                  [ 2. Federated Query Engine ]
                                (Query decomposition into sub-queries)
                                                │
                   ┌────────────────────────────┼────────────────────────────┐
                   ▼                            ▼                            ▼
            [ Hospital A ]               [ Hospital B ]               [ Hospital C ]
           (Medical History)             (Diagnostics)                 (Pharmacy)
                   │                            │                            │
            Local Evaluation             Local Evaluation             Local Evaluation
            (Blinded Tokens)             (Blinded Tokens)             (Blinded Tokens)
                   │                            │                            │
                   └────────────────────────────┼────────────────────────────┘
                                                │
                                    [ 3. SMPC / Secret Sharing ]
                          (Nodes exchange additive shares; raw counts never leave)
                                                │
                                [ 4. Differential Privacy Engine ]
                          (Laplace / Gaussian noise calibrated to sensitivity)
                                  + Privacy Budget Tracking (ε, δ)
                                                │
                                 [ 5. Immutable Audit Ledger ]
                       (Tamper-evident SHA-256 hash-chain block recording)
                                                │
                                                ▼
                                [ Privacy-Preserved Aggregate Result ]
```

---

## 4. User Example in Action

### Hospital A Asks:
> *"How many patients with condition X responded positively to treatment Y?"*

For example:
* **Condition X**: Type-2 Diabetes (`Hospital A: Medical History`)
* **Treatment Y**: Metformin with Positive Response (`Hospital C: Pharmacy`)
* **Biomarker Z**: Optional lab confirmation (`Hospital B: Diagnostics`)

### What Actually Happens:
1. **Hospital A** evaluates condition `Type-2 Diabetes` locally and identifies matching blinded tokens: $\{pt\_3a8f..., pt\_7e1c...\}$.
2. **Hospital C** evaluates prescription `Metformin` AND outcome `Positive` locally against candidate tokens.
3. Neither Hospital A nor Hospital C transfers raw patient names, medical histories, or dosages to each other.
4. If SMPC is enabled, local sub-counts are split into cryptographic additive secret shares.
5. The true count is perturbed with Laplace noise calibrated to $\epsilon = 1.0$ ($b = 1/\epsilon = 1.0$):
   $$\tilde{C} = \text{TrueCount} + \text{Laplace}(0, 1.0)$$
6. The researcher receives the perturbed answer (e.g. **53.2 patients**, with a 95% Confidence Interval of **[50.2, 56.2]**).
7. The query is permanently sealed into **Block #N** in the SHA-256 cryptographic audit ledger.

---

## 5. System Components & Code Structure

```
DB-project/
├── backend/
│   ├── database/
│   │   ├── tokens.py               # Cryptographic blinded tokens (HMAC-SHA256)
│   │   ├── generate_data.py        # Realistic multi-hospital synthetic clinical data
│   │   ├── hospital_nodes.py       # Isolated data access objects for Hospital A, B, C
│   │   ├── hospital_a.db           # Hospital A local SQLite database
│   │   ├── hospital_b.db           # Hospital B local SQLite database
│   │   └── hospital_c.db           # Hospital C local SQLite database
│   ├── privacy/
│   │   ├── differential_privacy.py # Laplace & Gaussian mechanisms, budget accountant
│   │   ├── smpc.py                 # Additive Secret Sharing & 3-party secure aggregation
│   │   └── anonymizer.py           # k-anonymity & l-diversity generalization/suppression
│   ├── security/
│   │   ├── access_control.py       # Role-Based & Purpose-Based Access Control (RBAC/PBAC)
│   │   └── audit_ledger.py         # Cryptographic SHA-256 hash-chain audit log
│   ├── federation/
│   │   └── orchestrator.py         # Federated query planner, dispatcher & pipeline coordinator
│   └── server.py                   # Starlette ASGI API & static file web server
├── frontend/
│   ├── index.html                  # Responsive modern web dashboard
│   ├── style.css                   # Custom CSS (Glassmorphism, dark theme, interactive topology)
│   └── app.js                      # UI logic, animated data flow, live chart/table rendering
├── tests/
│   ├── test_dp.py                  # Differential Privacy unit tests
│   ├── test_smpc.py                # SMPC secret sharing unit tests
│   ├── test_audit.py               # Cryptographic audit ledger & tamper detection tests
│   └── test_federation.py          # End-to-end multi-hospital query & PBAC tests
├── run_tests.py                    # Automated test runner (11/11 tests)
├── run.py                          # Single-command launcher script
└── README.md                       # Complete documentation & research answers
```

---

## 6. How to Run & Verify

### 1. Run Automated Test Suite
```powershell
python run_tests.py
```
*Executes all 11 unit and integration tests verifying DP noise scale, Gaussian variance, budget exhaustion, small cohort suppression, secret sharing, multi-party sum, SHA-256 chain verification, and tamper detection.*

### 2. Launch the Interactive Web Application
```powershell
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### 3. Interactive Highlights in the UI:
1. **Clinical Presets**: Click *"✨ User Question: Diabetes + Metformin Response"* to immediately run the exact scenario.
2. **Dynamic Epsilon Slider**: Adjust $\epsilon$ from $0.05$ (heavy privacy noise) to $5.0$ (minimal noise) and watch the confidence interval expand/contract in real time.
3. **SMPC Trace**: Expand the SMPC section to inspect step-by-step point-to-point share exchange.
4. **Inside Hospital Vaults**: Switch between Hospital A, B, and C to inspect local raw databases and verify isolation.
5. **$k$-Anonymity Microdata**: Generate a generalized tabular export with $k \ge 5$ and $\ell \ge 2$.
6. **Audit Ledger & Tamper Detection**: Click *"Simulate Tampering"* to maliciously alter Block #1, then watch the cryptographic chain instantly catch the breach in red! Click *"Restore Block"* to verify the chain turns green again.
