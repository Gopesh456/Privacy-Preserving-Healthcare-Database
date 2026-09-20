"""
Unit tests for Federated Query Orchestrator.
Verifies cross-hospital query execution, PBAC access control,
and k-anonymity microdata exports.
"""

from backend.federation.orchestrator import FederatedOrchestrator

def test_federated_joint_query_user_example():
    """
    Hospital A asks:
    'How many patients with condition X responded positively to treatment Y?'
    """
    orchestrator = FederatedOrchestrator()
    res = orchestrator.execute_collaborative_query(
        condition="Type-2 Diabetes",
        medication="Metformin",
        response_outcome="Positive",
        epsilon=1.0,
        use_dp=True,
        use_smpc=True,
        role="CLINICAL_RESEARCHER",
        purpose="CLINICAL_RESEARCH"
    )

    assert res["success"] is True
    assert "reported_count" in res["result"]
    assert "true_count" in res["result"]
    assert res["result"]["reported_count"] >= 0
    assert res["result"]["smpc"] is not None
    assert res["result"]["differential_privacy"]["epsilon"] == 1.0
    assert "audit_entry" in res

def test_pbac_authorization_rejection():
    orchestrator = FederatedOrchestrator()
    # Auditor role cannot execute clinical queries
    res = orchestrator.execute_collaborative_query(
        condition="Hypertension",
        role="EXTERNAL_AUDITOR",
        purpose="COMPLIANCE_AUDIT",
        epsilon=1.0
    )
    assert res["success"] is False
    assert res["error_type"] == "ACCESS_DENIED"

def test_k_anonymity_export():
    orchestrator = FederatedOrchestrator()
    res = orchestrator.export_anonymized_microdata(
        condition="Type-2 Diabetes",
        role="CLINICAL_RESEARCHER",
        purpose="CLINICAL_RESEARCH",
        k=5,
        l=2
    )
    assert res["success"] is True
    summary = res["anonymization_summary"]
    assert summary["k_threshold"] == 5
    assert summary["l_threshold"] == 2
    assert "retained_records" in summary
