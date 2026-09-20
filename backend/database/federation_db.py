"""
Federation Database & Inter-Hospital Coordination Engine.
Manages:
- Hospital Admin Credentials & Sessions
- Inter-Hospital Data Sharing Requests (Granular, Scoped)
- Review & Verification Workflow
- Real-Time Notification Bell & Dropdown queue
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_DIR = Path(__file__).parent
FEDERATION_DB_PATH = DB_DIR / "federation.db"

def get_federation_db():
    conn = sqlite3.connect(FEDERATION_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_federation_db():
    with get_federation_db() as conn:
        cursor = conn.cursor()

        # Admin Users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            hospital_id TEXT NOT NULL,
            hospital_name TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL
        );
        """)

        # Data Sharing Requests
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT UNIQUE NOT NULL,
            from_hospital TEXT NOT NULL,
            to_hospital TEXT NOT NULL,
            patient_token TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            requested_categories TEXT NOT NULL, -- JSON array e.g. ["medical_history", "diagnostics"]
            purpose TEXT NOT NULL,
            justification TEXT NOT NULL,
            status TEXT NOT NULL, -- 'PENDING', 'APPROVED', 'REJECTED'
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewer TEXT,
            approved_categories TEXT, -- JSON array
            shared_payload TEXT -- JSON string containing verified scoped data
        );
        """)

        # Notifications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id TEXT NOT NULL,
            type TEXT NOT NULL, -- 'REQUEST_RECEIVED', 'REQUEST_APPROVED', 'REQUEST_REJECTED'
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            request_id TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)

        # Seed Default Hospital Admin Accounts
        default_admins = [
            ("admin@hospital-a.org", "admin123", "node_a", "Hospital A", "Dr. Arthur Vance", "Chief Medical Officer"),
            ("admin@hospital-b.org", "admin123", "node_b", "Hospital B", "Dr. Beatrice Ramos", "Clinical Director"),
            ("admin@hospital-c.org", "admin123", "node_c", "Hospital C", "Dr. Charles Kim", "Head of Pharmacy")
        ]

        cursor.executemany("""
        INSERT OR REPLACE INTO admin_users (username, password, hospital_id, hospital_name, full_name, role)
        VALUES (?, ?, ?, ?, ?, ?);
        """, default_admins)

        conn.commit()

class FederationCoordinator:
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        init_federation_db()
        with get_federation_db() as conn:
            user = conn.execute(
                "SELECT * FROM admin_users WHERE username = ? AND password = ?",
                (username, password)
            ).fetchone()
            if user:
                return dict(user)
        return None

    @staticmethod
    def create_request(
        from_hospital: str,
        to_hospital: str,
        patient_token: str,
        patient_name: str,
        requested_categories: List[str],
        purpose: str,
        justification: str
    ) -> Dict[str, Any]:
        req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        now_ts = datetime.now(timezone.utc).isoformat()

        with get_federation_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO data_requests (
                request_id, from_hospital, to_hospital, patient_token, patient_name,
                requested_categories, purpose, justification, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """, (
                req_id, from_hospital, to_hospital, patient_token, patient_name,
                json.dumps(requested_categories), purpose, justification, now_ts
            ))

            # Send Notification to target hospital admin
            cats_formatted = ", ".join(c.replace("_", " ").title() for c in requested_categories)
            h_from_name = "Hospital " + from_hospital.replace("node_", "").upper()
            cursor.execute("""
            INSERT INTO notifications (hospital_id, type, title, message, request_id, created_at)
            VALUES (?, 'REQUEST_RECEIVED', ?, ?, ?, ?)
            """, (
                to_hospital,
                f"Data Access Request from {h_from_name}",
                f"{h_from_name} requests [{cats_formatted}] for patient {patient_name} ({patient_token[:10]}...). Purpose: {purpose}.",
                req_id,
                now_ts
            ))

            conn.commit()

        return {
            "success": True,
            "request_id": req_id,
            "status": "PENDING",
            "message": f"Data sharing request sent to {to_hospital.upper()} for verification."
        }

    @staticmethod
    def review_request(
        request_id: str,
        reviewer_hospital: str,
        reviewer_name: str,
        decision: str,  # 'APPROVED' or 'REJECTED'
        approved_categories: Optional[List[str]] = None,
        extracted_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        now_ts = datetime.now(timezone.utc).isoformat()

        with get_federation_db() as conn:
            cursor = conn.cursor()
            req = cursor.execute("SELECT * FROM data_requests WHERE request_id = ?", (request_id,)).fetchone()
            if not req:
                return {"success": False, "error": "Request not found."}

            if req["to_hospital"] != reviewer_hospital:
                return {"success": False, "error": "Unauthorized: Only target hospital can review this request."}

            payload_json = json.dumps(extracted_payload) if extracted_payload else None
            appr_cats_json = json.dumps(approved_categories or [])

            cursor.execute("""
            UPDATE data_requests
            SET status = ?, reviewed_at = ?, reviewer = ?, approved_categories = ?, shared_payload = ?
            WHERE request_id = ?
            """, (decision, now_ts, reviewer_name, appr_cats_json, payload_json, request_id))

            # Notify the requesting hospital
            from_h = req["from_hospital"]
            h_to_name = "Hospital " + reviewer_hospital.replace("node_", "").upper()
            if decision == "APPROVED":
                title = f"Access Approved by {h_to_name}"
                msg = f"{h_to_name} verified and approved access to requested data for {req['patient_name']}."
                ntype = "REQUEST_APPROVED"
            else:
                title = f"Access Declined by {h_to_name}"
                msg = f"{h_to_name} declined the data sharing request for {req['patient_name']}."
                ntype = "REQUEST_REJECTED"

            cursor.execute("""
            INSERT INTO notifications (hospital_id, type, title, message, request_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (from_h, ntype, title, msg, request_id, now_ts))

            conn.commit()

        return {"success": True, "request_id": request_id, "status": decision}

    @staticmethod
    def get_requests_for_hospital(hospital_id: str) -> Dict[str, Any]:
        with get_federation_db() as conn:
            incoming = conn.execute(
                "SELECT * FROM data_requests WHERE to_hospital = ? ORDER BY id DESC",
                (hospital_id,)
            ).fetchall()
            outgoing = conn.execute(
                "SELECT * FROM data_requests WHERE from_hospital = ? ORDER BY id DESC",
                (hospital_id,)
            ).fetchall()

            return {
                "incoming": [dict(r) for r in incoming],
                "outgoing": [dict(r) for r in outgoing]
            }

    @staticmethod
    def get_notifications(hospital_id: str) -> List[Dict[str, Any]]:
        with get_federation_db() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE hospital_id = ? ORDER BY id DESC LIMIT 20",
                (hospital_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def mark_notifications_read(hospital_id: str):
        with get_federation_db() as conn:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE hospital_id = ?", (hospital_id,))
            conn.commit()
