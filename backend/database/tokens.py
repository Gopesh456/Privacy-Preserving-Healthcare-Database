"""
Cryptographic Blinded Pseudonym Token Generator.
Simulates cross-hospital Private Entity Linkage.
Each hospital maps local patient national IDs or SSNs into a blind cryptographic token
using HMAC-SHA256 with a federated salt, ensuring no plain PII is ever shared.
"""
import hmac
import hashlib

# Federation-wide secret salt established via secure key exchange
FEDERATION_SALT = b"PP-HDB-FEDERATION-SECRET-SALT-2026-KEY-V1"

def generate_blinded_token(national_id: str) -> str:
    """
    Computes a deterministic cryptographic blinded token for a patient identifier.
    Hospital A, B, and C can compute this independently for the same patient
    without ever sharing the national_id.
    """
    h = hmac.new(FEDERATION_SALT, national_id.encode("utf-8"), hashlib.sha256)
    # Return 16-byte hex token (e.g. 'tok_a3f89e1b2c4d5e6f')
    return f"pt_{h.hexdigest()[:16]}"
