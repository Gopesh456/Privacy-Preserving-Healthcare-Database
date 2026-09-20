"""
Hospital Node Interfaces.
Each class represents an independent hospital server/database enclave.
Nodes never reveal raw patient records to outside callers.
They only return matched blinded tokens, local aggregate values, or secret shares.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_DIR = Path(__file__).parent

class HospitalNode:
    def __init__(self, node_id: str, db_name: str, name: str, domain: str):
        self.node_id = node_id
        self.db_path = DB_DIR / db_name
        self.name = name
        self.domain = domain

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            table_name = "patients" if self.node_id == "node_a" else ("diagnostics" if self.node_id == "node_b" else "prescriptions")
            total = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            unique_patients = cursor.execute(f"SELECT COUNT(DISTINCT token) FROM {table_name}").fetchone()[0]
            return {
                "node_id": self.node_id,
                "name": self.name,
                "domain": self.domain,
                "total_records": total,
                "unique_patients": unique_patients
            }

    def inspect_local_vault(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Demonstration tool only: view the raw data trapped inside this hospital node
        to prove to the user that it never leaves this hospital.
        """
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            table_name = "patients" if self.node_id == "node_a" else ("diagnostics" if self.node_id == "node_b" else "prescriptions")
            rows = cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

class HospitalANode(HospitalNode):
    """Hospital A: Medical History and Demographics"""
    def __init__(self):
        super().__init__("node_a", "hospital_a.db", "Hospital A (Clinical History)", "Medical History & Demographics")

    def query_matching_tokens(self, condition: Optional[str] = None, severity: Optional[str] = None) -> List[str]:
        """
        Evaluates local conditions inside Hospital A and returns matching blinded tokens.
        """
        query = "SELECT token FROM patients WHERE 1=1"
        params = []
        if condition:
            query += " AND condition = ?"
            params.append(condition)
        if severity:
            query += " AND severity = ?"
            params.append(severity)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
            return [r[0] for r in rows]

    def get_cohort_attributes(self, tokens: List[str]) -> List[Dict[str, Any]]:
        """Used exclusively for k-anonymity microdata synthesis"""
        if not tokens:
            return []
        placeholders = ",".join("?" for _ in tokens)
        query = f"SELECT token, age, gender, condition, severity FROM patients WHERE token IN ({placeholders})"
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(query, tokens).fetchall()
            return [dict(r) for r in rows]

class HospitalBNode(HospitalNode):
    """Hospital B: Diagnostics and Lab Reports"""
    def __init__(self):
        super().__init__("node_b", "hospital_b.db", "Hospital B (Diagnostics)", "Laboratory & Biomarkers")

    def query_matching_tokens(self, candidate_tokens: Optional[List[str]] = None,
                              biomarker: Optional[str] = None,
                              abnormal_only: bool = False,
                              max_value: Optional[float] = None,
                              min_value: Optional[float] = None) -> List[str]:
        query = "SELECT DISTINCT token FROM diagnostics WHERE 1=1"
        params = []
        if biomarker:
            query += " AND biomarker_name = ?"
            params.append(biomarker)
        if abnormal_only:
            query += " AND abnormal_flag = 1"
        if max_value is not None:
            query += " AND biomarker_value <= ?"
            params.append(max_value)
        if min_value is not None:
            query += " AND biomarker_value >= ?"
            params.append(min_value)

        if candidate_tokens is not None:
            if not candidate_tokens:
                return []
            placeholders = ",".join("?" for _ in candidate_tokens)
            query += f" AND token IN ({placeholders})"
            params.extend(candidate_tokens)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
            return [r[0] for r in rows]

class HospitalCNode(HospitalNode):
    """Hospital C: Pharmacy and Prescriptions"""
    def __init__(self):
        super().__init__("node_c", "hospital_c.db", "Hospital C (Pharmacy)", "Prescriptions & Outcomes")

    def query_matching_tokens(self, candidate_tokens: Optional[List[str]] = None,
                              medication: Optional[str] = None,
                              response_outcome: Optional[str] = None,
                              min_adherence: Optional[float] = None) -> List[str]:
        query = "SELECT DISTINCT token FROM prescriptions WHERE 1=1"
        params = []
        if medication:
            query += " AND medication = ?"
            params.append(medication)
        if response_outcome:
            query += " AND response_outcome = ?"
            params.append(response_outcome)
        if min_adherence is not None:
            query += " AND adherence_rate >= ?"
            params.append(min_adherence)

        if candidate_tokens is not None:
            if not candidate_tokens:
                return []
            placeholders = ",".join("?" for _ in candidate_tokens)
            query += f" AND token IN ({placeholders})"
            params.extend(candidate_tokens)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, params).fetchall()
            return [r[0] for r in rows]

    def get_cohort_prescriptions(self, tokens: List[str]) -> List[Dict[str, Any]]:
        if not tokens:
            return []
        placeholders = ",".join("?" for _ in tokens)
        query = f"SELECT token, medication, response_outcome FROM prescriptions WHERE token IN ({placeholders})"
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(query, tokens).fetchall()
            return [dict(r) for r in rows]
