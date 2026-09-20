"""
Unit tests for Secure Multi-Party Computation (SMPC).
Verifies Additive Secret Sharing and multi-party secure sum protocol.
"""

from backend.privacy.smpc import AdditiveSecretSharing, SMPCSecureAggregator

def test_additive_secret_sharing():
    ass = AdditiveSecretSharing()
    secret = 42
    shares = ass.generate_shares(secret, num_parties=3)

    assert len(shares) == 3
    # Any single share should be within the field modulus
    for s in shares:
        assert 0 <= s < ass.modulus

    reconstructed = ass.reconstruct_secret(shares)
    assert reconstructed == secret

def test_smpc_secure_sum_protocol():
    aggregator = SMPCSecureAggregator()
    inputs = {
        "Hospital_A": 25,
        "Hospital_B": 40,
        "Hospital_C": 35
    }
    expected_total = 25 + 40 + 35  # 100

    result = aggregator.run_secure_sum(inputs)
    assert result["reconstructed_total"] == expected_total
    assert len(result["protocol_trace"]) >= 4
    assert len(result["node_aggregated_shares"]) == 3
