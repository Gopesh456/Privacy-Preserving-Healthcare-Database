"""
Automated Test Runner for Privacy-Preserving Healthcare Database.
Runs all unit and integration tests across DP, SMPC, Audit Ledger, and Federation.
"""

import sys
import unittest

def run_all_tests():
    print("======================================================================")
    print("Running PP-HDB Privacy & Security Test Suite")
    print("======================================================================")

    import tests.test_dp as t1
    import tests.test_smpc as t2
    import tests.test_audit as t3
    import tests.test_federation as t4

    # Run DP tests
    print("\n[1/4] Testing Differential Privacy Engine...")
    t1.test_laplace_mechanism_output()
    t1.test_privacy_budget_exhaustion()
    t1.test_small_cohort_suppression()
    t1.test_gaussian_mechanism()
    print("  -> Laplace noise, Gaussian noise, budget accounting, and suppression PASSED.")

    # Run SMPC tests
    print("\n[2/4] Testing Secure Multi-Party Computation...")
    t2.test_additive_secret_sharing()
    t2.test_smpc_secure_sum_protocol()
    print("  -> Additive secret sharing and 3-party secure aggregation PASSED.")

    # Run Audit tests
    print("\n[3/4] Testing Cryptographic Audit Ledger...")
    t3.test_audit_ledger_genesis_and_logging()
    t3.test_tamper_detection()
    print("  -> Genesis creation, SHA-256 hash chaining, and tamper detection PASSED.")

    # Run Federation tests
    print("\n[4/5] Testing Federated Multi-Hospital Orchestrator...")
    t4.test_federated_joint_query_user_example()
    t4.test_pbac_authorization_rejection()
    t4.test_k_anonymity_export()
    print("  -> Multi-hospital joint queries, PBAC, and k-anonymity export PASSED.")

    # Run Inter-Hospital Sharing tests
    print("\n[5/5] Testing Inter-Hospital Discovery, Request & Verification Workflow...")
    import tests.test_inter_hospital_sharing as t5
    t5.test_inter_hospital_discovery_and_sharing_flow()
    print("  -> Privacy-preserving discovery, scoped requests, and verified data release PASSED.")

    print("\n======================================================================")
    print("ALL TEST SUITES PASSED (12/12)")
    print("======================================================================")
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
