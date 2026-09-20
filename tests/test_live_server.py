"""
Live HTTP Verification Script for PP-HDB Server.
Tests all endpoints against http://127.0.0.1:8000.
Includes discovery, notifications, and inter-hospital data sharing workflow.
"""

import urllib.request
import json

def test_live_endpoints():
    base = "http://127.0.0.1:8000"

    print("=" * 65)
    print("Testing Live PP-HDB Multi-Hospital Server Endpoints")
    print("=" * 65)

    # 1. Test Index
    with urllib.request.urlopen(base + "/") as resp:
        content = resp.read()
        print(f"[1] GET / -> HTTP {resp.status} ({len(content)} bytes served)")
        assert resp.status == 200

    # 2. Test Hospital Admin Authentication
    req = urllib.request.Request(
        base + "/api/auth/login",
        data=json.dumps({"username": "admin@hospital-a.org", "password": "admin123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"[2] POST /api/auth/login -> HTTP {resp.status} (Logged in: {data['user']['full_name']})")
        assert data["success"] is True

    # 3. Test Local Patient Roster for Hospital A
    with urllib.request.urlopen(base + "/api/patient/search?hospital_id=node_a&q=") as resp:
        data = json.loads(resp.read().decode())
        patients = data.get("patients", [])
        print(f"[3] GET /api/patient/search?hospital_id=node_a -> HTTP {resp.status} ({len(patients)} local patients)")
        assert len(patients) > 0
        sarah = next((p for p in patients if p["name"] == "Sarah Jenkins"), None)
        assert sarah is not None, "Sarah Jenkins must be in Hospital A"
        sarah_token = sarah["token"]

    # 4. Test Privacy-Preserving Discovery from Hospital B
    # When searching Sarah Jenkins from Hospital B, it must show:
    # local_present: False, Hospital A: Present, Hospital C: Absent
    with urllib.request.urlopen(base + f"/api/patient/discover?hospital_id=node_b&q=Sarah%20Jenkins") as resp:
        data = json.loads(resp.read().decode())
        disc = data["discovery"]
        print(f"[4] GET /api/patient/discover (Hospital B searches Sarah Jenkins) -> HTTP {resp.status}")
        print(f"    - Found Anywhere: {disc['found_anywhere']}")
        print(f"    - Present in Hospital B: {disc['local_present']}")
        h_a = next(p for p in disc["federation_presence"] if p["hospital_id"] == "node_a")
        print(f"    - Hospital A Availability: Present={h_a['present']}, History={h_a['categories']['medical_history']}, Labs={h_a['categories']['diagnostics']}")
        assert disc["found_anywhere"] is True
        assert disc["local_present"] is False
        assert h_a["present"] is True

    # 5. Test Hospital B Requesting Scoped Data from Hospital A
    req = urllib.request.Request(
        base + "/api/sharing/request",
        data=json.dumps({
            "from_hospital": "node_b",
            "to_hospital": "node_a",
            "patient_token": sarah_token,
            "patient_name": "Sarah Jenkins",
            "requested_categories": ["medical_history", "diagnostics"],
            "purpose": "CONTINUATION_OF_CARE",
            "justification": "Patient transfer to Hospital B cardiology clinic."
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        req_id = data["request_id"]
        print(f"[5] POST /api/sharing/request -> HTTP {resp.status} (Created: {req_id})")
        assert data["success"] is True

    # 6. Test Hospital A Notification Receipt
    with urllib.request.urlopen(base + "/api/notifications?hospital_id=node_a") as resp:
        data = json.loads(resp.read().decode())
        notifs = data.get("notifications", [])
        unread = data.get("unread_count", 0)
        print(f"[6] GET /api/notifications (Hospital A) -> HTTP {resp.status} ({len(notifs)} notifications, {unread} unread)")
        assert any(n["request_id"] == req_id for n in notifs)

    # 7. Test Hospital A Review & Verified Approval
    req = urllib.request.Request(
        base + "/api/sharing/review",
        data=json.dumps({
            "request_id": req_id,
            "reviewer_hospital": "node_a",
            "reviewer_name": "Dr. Arthur Vance (CMO)",
            "decision": "APPROVED",
            "approved_categories": ["medical_history", "diagnostics"]
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"[7] POST /api/sharing/review -> HTTP {resp.status} (Decision: {data['status']})")
        assert data["success"] is True

    # 8. Test Hospital B Receiving Verified Shared Payload
    with urllib.request.urlopen(base + "/api/sharing/requests?hospital_id=node_b") as resp:
        data = json.loads(resp.read().decode())
        out_req = next(r for r in data["requests"]["outgoing"] if r["request_id"] == req_id)
        payload = json.loads(out_req["shared_payload"])
        print(f"[8] GET /api/sharing/requests (Hospital B) -> HTTP {resp.status}")
        print(f"    - Payload Categories: {list(payload.keys())}")
        print(f"    - Data Minimization Check: Prescriptions in payload? {'prescriptions' in payload}")
        assert "medical_history" in payload
        assert "diagnostics" in payload
        assert "prescriptions" not in payload, "Prescriptions must not leak (data minimization)"

    # 9. Test Hospital B Adding Clinical Encounter
    req = urllib.request.Request(
        base + "/api/patient/encounter/add",
        data=json.dumps({
            "hospital_id": "node_b",
            "token": sarah_token,
            "category": "diagnostics",
            "encounter_data": {
                "test_name": "Hospital B Follow-up Panel",
                "biomarker_name": "HbA1c Followup",
                "biomarker_value": 6.2,
                "unit": "%",
                "abnormal_flag": 0,
                "test_year": 2026
            }
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"[9] POST /api/patient/encounter/add -> HTTP {resp.status} (Encounter ID: {data['encounter_id']})")
        assert data["success"] is True

    # 10. Test Audit Ledger Verification
    req = urllib.request.Request(base + "/api/audit/verify", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"[10] POST /api/audit/verify -> HTTP {resp.status} (Ledger Valid: {data['status']['valid']}, Total Blocks: {data['status']['total_blocks']})")
        assert data["status"]["valid"] is True

    print("\n[OK] ALL 10 LIVE SERVER MULTI-HOSPITAL ENDPOINTS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_live_endpoints()
