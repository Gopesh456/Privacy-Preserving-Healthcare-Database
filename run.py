"""
PP-HDB Launcher Script.
Verifies database initialization and starts the Starlette/Uvicorn server.
"""

import sys
import os
from pathlib import Path

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.database.generate_data import seed_databases, DB_A_PATH, DB_B_PATH, DB_C_PATH

def main():
    print("=" * 65)
    print("  PP-HDB: Privacy-Preserving Healthcare Database System")
    print("=" * 65)

    # Check if databases exist; if not, seed them
    if not (DB_A_PATH.exists() and DB_B_PATH.exists() and DB_C_PATH.exists()):
        print("\n[*] Initializing synthetic multi-hospital databases...")
        seed_databases(total_patients=600)
    else:
        print("\n[OK] Hospital databases detected (Hospital A, Hospital B, Hospital C).")

    print("[*] Starting Privacy-Preserving Healthcare Database Web Server...")
    print("    Access the Interactive Web Application at:")
    print("    --> http://127.0.0.1:8000\n")

    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

if __name__ == "__main__":
    main()
