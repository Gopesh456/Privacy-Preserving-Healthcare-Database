"""
Unit & Integration Tests for Inter-Hospital Granular Data Sharing.
Verifies:
1. Multi-hospital full EHR storage.
2. Privacy-preserving discovery / presence checking across nodes.
3. Scoped data requests with PBAC purpose validation.
4. Review & verification workflow with field-level scoping.
5. Notification delivery between hospitals.
6. Data minimization enforcement (unrequested categories withheld).
"""

from backend.federation.orchestrator import FederatedOrchestrator
from backend.database.hospital_nodes import hospital_a_node, hospital_b_node
from backend.database.federation_db import FederationCoordinator

def test_inter_hospital_discovery_and_sharing_flow():
    orchestrator = FederatedOrchestrator()

    # Step 1: Discover Sarah Jenkins from Hospital B
    # Sarah Jenkins visited Hospital A first, so Hospital B should see:
    # local_present: False, Hospital A: Present, Hospital C: Absent
    discovery = orchestrator.discover_patient("node_b", "Sarah Jenkins")
    assert discovery["found_anywhere"] is True
    assert discovery["local_present"] is False

    hosp_a_presence = next(p for p in discovery["federation_presence"] if p["hospital_id"] == "node_a")
    assert hosp_a_presence["present"] is True
    assert hosp_a_presence["categories"]["medical_history"] is True
    assert hosp_a_presence["categories"]["diagnostics"] is True

    token = discovery["patient_token"]
    assert token is not None

    # Step 2: Hospital B creates a scoped request to Hospital A
    # Hospital B requests ONLY medical_history and diagnostics (omits prescriptions)
    req_res = orchestrator.request_patient_data(
        from_hospital="node_b",
        to_hospital="node_a",
        patient_token=token,
        patient_name="Sarah Jenkins",
        requested_categories=["medical_history", "diagnostics"],
        purpose="CONTINUATION_OF_CARE",
        justification="Patient presented at Hospital B outpatient clinic for ongoing evaluation."
    )
    assert req_res["success"] is True
    req_id = req_res["request_id"]

    # Step 3: Verify notification is generated for Hospital A
    notifs_a = FederationCoordinator.get_notifications("node_a")
    assert any(n["request_id"] == req_id for n in notifs_a)

    # Step 4: Hospital A reviews and approves ONLY the requested categories
    review_res = orchestrator.review_patient_data_request(
        request_id=req_id,
        reviewer_hospital="node_a",
        reviewer_name="Dr. Arthur Vance (Hospital A CMO)",
        decision="APPROVED",
        approved_categories=["medical_history", "diagnostics"]
    )
    assert review_res["success"] is True

    # Step 5: Hospital B inspects the shared payload
    requests_b = FederationCoordinator.get_requests_for_hospital("node_b")
    approved_req = next(r for r in requests_b["outgoing"] if r["request_id"] == req_id)
    assert approved_req["status"] == "APPROVED"
    assert approved_req["shared_payload"] is not None

    import json
    payload = json.loads(approved_req["shared_payload"])
    # Verified that medical_history and diagnostics are present
    assert "medical_history" in payload
    assert "diagnostics" in payload
    # DATA MINIMIZATION: prescriptions MUST NOT be present because it wasn't requested/approved!
    assert "prescriptions" not in payload

    # Step 6: Hospital B adds a local encounter for this patient
    encounter_res = hospital_b_node.add_clinical_encounter(
        category="diagnostics",
        token=token,
        data={
            "test_name": "Hospital B Follow-up Panel",
            "biomarker_name": "HbA1c Followup",
            "biomarker_value": 6.4,
            "unit": "%",
            "abnormal_flag": 0,
            "test_year": 2026
        }
    )
    assert encounter_res["success"] is True

    print("Inter-Hospital Sharing Test PASSED successfully!")

if __name__ == "__main__":
    test_inter_hospital_discovery_and_sharing_flow()
