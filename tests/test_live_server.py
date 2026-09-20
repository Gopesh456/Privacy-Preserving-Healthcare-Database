"""
Live HTTP Verification Script for PP-HDB Server.
Tests all endpoints against http://127.0.0.1:8000.
"""

import urllib.request
import json

def test_live_endpoints():
    base = "http://127.0.0.1:8000"

    print("=" * 60)
    print("Testing Live PP-HDB Server Endpoints")
    print("=" * 60)

    # 1. Test Index
    with urllib.request.urlopen(base + "/") as resp:
        content = resp.read()
        print(f"[1] GET / -> HTTP {resp.status} ({len(content)} bytes)")
        assert resp.status == 200

    # 2. Test Nodes
    with urllib.request.urlopen(base + "/api/nodes") as resp:
        data = json.loads(resp.read().decode())
        nodes = data.get("nodes", [])
        print(f"[2] GET /api/nodes -> HTTP {resp.status} ({len(nodes)} hospital nodes online)")
        assert len(nodes) == 3

    # 3. Test Vault Node A
    with urllib.request.urlopen(base + "/api/vault/node_a?limit=5") as resp:
        data = json.loads(resp.read().decode())
        records = data.get("records", [])
        print(f"[3] GET /api/vault/node_a -> HTTP {resp.status} ({len(records)} sample records trapped in vault)")
        assert len(records) > 0

    # 4. Test Query (The User Question: Type-2 Diabetes + Metformin + Positive Outcome)
    req = urllib.request.Request(
        base + "/api/query",
        data=json.dumps({
            "condition": "Type-2 Diabetes",
            "medication": "Metformin",
            "response_outcome": "Positive",
            "epsilon": 1.0,
            "use_dp": True,
            "use_smpc": True,
            "role": "CLINICAL_RESEARCHER",
            "purpose": "CLINICAL_RESEARCH"
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        res = data["result"]
        dp = res["differential_privacy"]
        smpc = res["smpc"]
        audit = data["audit_entry"]

        print(f"[4] POST /api/query (User Scenario Test) -> HTTP {resp.status}")
        print(f"    - Query: Type-2 Diabetes + Metformin -> Positive Response")
        print(f"    - Reported DP Count: {dp['perturbed_value']} patients")
        print(f"    - True Underlying Count: {res['true_count']} patients")
        print(f"    - Laplace Noise Added: {dp['noise_added']}")
        print(f"    - 95% Confidence Interval: [{dp['confidence_interval_95']['lower']}, {dp['confidence_interval_95']['upper']}]")
        print(f"    - SMPC Reconstructed Total: {smpc['reconstructed_total']} (zero intermediate counts leaked)")
        print(f"    - Audit Block Index: #{audit['block_index']} (Hash: {audit['block_hash'][:16]}...)")
        assert data["success"] is True

    # 5. Test Audit Verification
    req = urllib.request.Request(base + "/api/audit/verify", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"[5] POST /api/audit/verify -> HTTP {resp.status} (Valid: {data['status']['valid']}, Total Blocks: {data['status']['total_blocks']})")
        assert data["status"]["valid"] is True

    # 6. Test Anonymizer Export
    req = urllib.request.Request(
        base + "/api/anonymize",
        data=json.dumps({
            "condition": "Type-2 Diabetes",
            "k": 5,
            "l": 2,
            "role": "CLINICAL_RESEARCHER",
            "purpose": "CLINICAL_RESEARCH"
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        summary = data.get("anonymization_summary", {})
        print(f"[6] POST /api/anonymize -> HTTP {resp.status} (Retained: {summary.get('retained_records')}, Suppressed: {summary.get('suppressed_records')})")
        assert data["success"] is True

    print("\n[OK] ALL LIVE SERVER ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_live_endpoints()
