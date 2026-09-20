"""
Unit tests for Cryptographic Audit Ledger.
Verifies Genesis block creation, sequential block addition,
cryptographic verification, and tamper detection.
"""

from backend.security.audit_ledger import AuditLedger

def test_audit_ledger_genesis_and_logging():
    ledger = AuditLedger()
    assert len(ledger.chain) == 1
    genesis = ledger.chain[0]
    assert genesis.index == 0
    assert genesis.researcher == "SYSTEM_GENESIS"
    assert genesis.previous_hash == "0" * 64

    # Log new query
    block = ledger.log_query(
        researcher="Dr. Sarah Lin",
        role="CLINICAL_RESEARCHER",
        purpose="CLINICAL_RESEARCH",
        query_type="FEDERATED_COHORT_QUERY",
        query_parameters={"condition": "Type-2 Diabetes"},
        participating_nodes=["Hospital A", "Hospital B"],
        epsilon_spent=1.0
    )
    assert block.index == 1
    assert block.previous_hash == genesis.block_hash
    assert len(ledger.chain) == 2

    # Integrity verification
    verification = ledger.verify_integrity()
    assert verification["valid"] is True
    assert verification["total_blocks"] == 2

def test_tamper_detection():
    ledger = AuditLedger()
    ledger.log_query(
        researcher="Dr. Sarah Lin",
        role="CLINICAL_RESEARCHER",
        purpose="CLINICAL_RESEARCH",
        query_type="FEDERATED_COHORT_QUERY",
        query_parameters={"condition": "Type-2 Diabetes"},
        participating_nodes=["Hospital A"],
        epsilon_spent=1.0
    )
    ledger.log_query(
        researcher="Dr. James Patel",
        role="CLINICAL_RESEARCHER",
        purpose="TREATMENT_EFFICACY",
        query_type="FEDERATED_COHORT_QUERY",
        query_parameters={"condition": "Hypertension"},
        participating_nodes=["Hospital A", "Hospital C"],
        epsilon_spent=0.5
    )

    # Initial check passes
    assert ledger.verify_integrity()["valid"] is True

    # Tamper with block #1
    tamper_res = ledger.simulate_tampering(1, fake_researcher="ROGUE_ACTOR")
    assert tamper_res["success"] is True

    # Integrity check MUST fail and detect corrupted block 1
    check = ledger.verify_integrity()
    assert check["valid"] is False
    assert check["corrupted_block_index"] == 1

    # Restore block #1 and verify it passes again
    ledger.restore_block(1, tamper_res["original_field"])
    assert ledger.verify_integrity()["valid"] is True
