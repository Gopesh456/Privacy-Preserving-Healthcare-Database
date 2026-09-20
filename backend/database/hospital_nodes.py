"""
Hospital Node Interfaces for Full-Spectrum Hospital Enclaves.
Each hospital node (Hospital A, Hospital B, Hospital C) manages its own
independent database with complete medical records (history, labs, prescriptions).

Provides:
- Local patient profile retrieval
- Blinded presence checking (for privacy-preserving discovery across the federation)
- Local patient registration and clinical encounter additions
- Verified scoped record extraction (enforcing data minimization)
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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            patients_count = cursor.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
            history_count = cursor.execute("SELECT COUNT(*) FROM medical_history").fetchone()[0]
            diag_count = cursor.execute("SELECT COUNT(*) FROM diagnostics").fetchone()[0]
            rx_count = cursor.execute("SELECT COUNT(*) FROM prescriptions").fetchone()[0]

            return {
                "node_id": self.node_id,
                "name": self.name,
                "domain": self.domain,
                "total_patients": patients_count,
                "total_history_records": history_count,
                "total_diagnostic_records": diag_count,
                "total_prescription_records": rx_count
            }

    def search_local_patients(self, search_term: str = "") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if not search_term.strip():
                rows = cursor.execute("""
                SELECT patient_id, national_id, token, name, age, gender, blood_group, allergies, primary_condition
                FROM patients ORDER BY patient_id ASC LIMIT 25
                """).fetchall()
            else:
                q = f"%{search_term.strip()}%"
                rows = cursor.execute("""
                SELECT patient_id, national_id, token, name, age, gender, blood_group, allergies, primary_condition
                FROM patients
                WHERE name LIKE ? OR national_id LIKE ? OR token LIKE ? OR primary_condition LIKE ?
                ORDER BY patient_id ASC LIMIT 25
                """, (q, q, q, q)).fetchall()

            return [dict(r) for r in rows]

    def get_patient_full_profile(self, token: str) -> Optional[Dict[str, Any]]:
        """Returns full local clinical profile for a patient token."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            patient = cursor.execute("SELECT * FROM patients WHERE token = ?", (token,)).fetchone()
            if not patient:
                return None

            history = cursor.execute("SELECT * FROM medical_history WHERE token = ? ORDER BY diagnosis_year DESC", (token,)).fetchall()
            diagnostics = cursor.execute("SELECT * FROM diagnostics WHERE token = ? ORDER BY test_year DESC", (token,)).fetchall()
            prescriptions = cursor.execute("SELECT * FROM prescriptions WHERE token = ?", (token,)).fetchall()

            return {
                "patient": dict(patient),
                "medical_history": [dict(h) for h in history],
                "diagnostics": [dict(d) for d in diagnostics],
                "prescriptions": [dict(p) for p in prescriptions]
            }

    def check_patient_presence(self, token: str) -> Dict[str, Any]:
        """
        Zero-Knowledge Presence Check.
        Informs the federation IF this hospital has data for the patient and which categories,
        WITHOUT leaking any clinical content or sensitive fields prior to authorization.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            patient = cursor.execute("SELECT name, national_id FROM patients WHERE token = ?", (token,)).fetchone()

            if not patient:
                return {
                    "hospital_id": self.node_id,
                    "hospital_name": self.name,
                    "present": False,
                    "patient_name_masked": None,
                    "categories": {
                        "medical_history": False,
                        "diagnostics": False,
                        "prescriptions": False
                    }
                }

            h_count = cursor.execute("SELECT COUNT(*) FROM medical_history WHERE token = ?", (token,)).fetchone()[0]
            d_count = cursor.execute("SELECT COUNT(*) FROM diagnostics WHERE token = ?", (token,)).fetchone()[0]
            p_count = cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE token = ?", (token,)).fetchone()[0]

            # Mask patient name e.g. "S*** J***" for privacy preview
            parts = patient["name"].split()
            masked_name = " ".join(p[0] + "***" for p in parts) if parts else "Anonymous"

            return {
                "hospital_id": self.node_id,
                "hospital_name": self.name,
                "present": True,
                "patient_name_masked": masked_name,
                "categories": {
                    "medical_history": h_count > 0,
                    "diagnostics": d_count > 0,
                    "prescriptions": p_count > 0
                },
                "counts": {
                    "history_entries": h_count,
                    "diagnostic_reports": d_count,
                    "prescriptions": p_count
                }
            }

    def extract_scoped_records(self, token: str, approved_categories: List[str]) -> Dict[str, Any]:
        """
        Extracts ONLY the verified and approved categories for an authorized request.
        Enforces Data Minimization.
        """
        result = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            patient = cursor.execute("SELECT * FROM patients WHERE token = ?", (token,)).fetchone()
            if not patient:
                return {"error": "Patient not found in this hospital."}

            result["patient_demographics"] = {
                "token": patient["token"],
                "name": patient["name"],
                "age": patient["age"],
                "gender": patient["gender"],
                "blood_group": patient["blood_group"],
                "allergies": patient["allergies"]
            }

            if "medical_history" in approved_categories:
                rows = cursor.execute("SELECT * FROM medical_history WHERE token = ?", (token,)).fetchall()
                result["medical_history"] = [dict(r) for r in rows]

            if "diagnostics" in approved_categories:
                rows = cursor.execute("SELECT * FROM diagnostics WHERE token = ?", (token,)).fetchall()
                result["diagnostics"] = [dict(r) for r in rows]

            if "prescriptions" in approved_categories:
                rows = cursor.execute("SELECT * FROM prescriptions WHERE token = ?", (token,)).fetchall()
                result["prescriptions"] = [dict(r) for r in rows]

        return result

    def register_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO patients (national_id, token, name, age, gender, blood_group, allergies, primary_condition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                data["national_id"],
                data["token"],
                data["name"],
                int(data["age"]),
                data["gender"],
                data.get("blood_group", "Unknown"),
                data.get("allergies", "None Known"),
                data.get("primary_condition", "Under Evaluation")
            ))
            conn.commit()
            return {"success": True, "patient_id": cursor.lastrowid}

    def add_clinical_encounter(self, category: str, token: str, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if category == "medical_history":
                cursor.execute("""
                INSERT INTO medical_history (token, condition, icd10, severity, diagnosis_year, clinical_notes)
                VALUES (?, ?, ?, ?, ?, ?);
                """, (
                    token,
                    data["condition"],
                    data.get("icd10", "R69"),
                    data.get("severity", "Moderate"),
                    int(data.get("diagnosis_year", 2026)),
                    data.get("clinical_notes", "Routine consultation notes recorded.")
                ))
            elif category == "diagnostics":
                cursor.execute("""
                INSERT INTO diagnostics (token, test_name, biomarker_name, biomarker_value, unit, abnormal_flag, test_year)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    token,
                    data["test_name"],
                    data["biomarker_name"],
                    float(data["biomarker_value"]),
                    data.get("unit", "units"),
                    1 if data.get("abnormal_flag") else 0,
                    int(data.get("test_year", 2026))
                ))
            elif category == "prescriptions":
                cursor.execute("""
                INSERT INTO prescriptions (token, medication, dosage, frequency, days_supply, adherence_rate, response_outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    token,
                    data["medication"],
                    data["dosage"],
                    data.get("frequency", "Once Daily"),
                    int(data.get("days_supply", 30)),
                    float(data.get("adherence_rate", 0.95)),
                    data.get("response_outcome", "Positive")
                ))
            else:
                return {"success": False, "error": f"Unknown category: {category}"}

            conn.commit()
            return {"success": True, "encounter_id": cursor.lastrowid}

    def inspect_local_vault(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("""
            SELECT p.token, p.name, p.age, p.gender, p.primary_condition,
                   (SELECT count(*) FROM medical_history m WHERE m.token = p.token) as history_count,
                   (SELECT count(*) FROM diagnostics d WHERE d.token = p.token) as diag_count,
                   (SELECT count(*) FROM prescriptions r WHERE r.token = p.token) as rx_count
            FROM patients p
            LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

# Concrete hospital node instances
hospital_a_node = HospitalNode("node_a", "hospital_a.db", "Hospital A", "General Medicine & EHR")
hospital_b_node = HospitalNode("node_b", "hospital_b.db", "Hospital B", "Diagnostics & Research")
hospital_c_node = HospitalNode("node_c", "hospital_c.db", "Hospital C", "Pharmacy & Therapeutics")

def get_hospital_node(node_id: str) -> Optional[HospitalNode]:
    if node_id == "node_a":
        return hospital_a_node
    elif node_id == "node_b":
        return hospital_b_node
    elif node_id == "node_c":
        return hospital_c_node
    return None
