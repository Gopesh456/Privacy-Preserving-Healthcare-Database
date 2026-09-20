"""
Synthetic Healthcare Database Generator for Federated Full-Spectrum Hospital Nodes.
Each hospital (A, B, C) maintains its own full local clinical database:
- patients (demographics, blood group, allergies)
- medical_history (conditions, ICD-10, severity, clinical notes)
- diagnostics (lab tests, biomarkers, units, abnormal flags)
- prescriptions (drugs, dosages, frequencies, treatment outcomes)

Simulates patients visiting Hospital A first, then Hospital B, enabling
inter-hospital discovery, scoped data requests, review, and verification.
"""

import sqlite3
import random
import os
from pathlib import Path
from backend.database.tokens import generate_blinded_token
from backend.database.federation_db import init_federation_db

DB_DIR = Path(__file__).parent
DB_A_PATH = DB_DIR / "hospital_a.db"
DB_B_PATH = DB_DIR / "hospital_b.db"
DB_C_PATH = DB_DIR / "hospital_c.db"

FIRST_NAMES = [
    "Sarah", "Marcus", "Elena", "David", "Amina", "Carlos", "Priya", "Liam", "Grace",
    "Kenji", "Fatima", "Alexander", "Chloe", "Mateo", "Hannah", "Tariq", "Olivia",
    "Noah", "Sophia", "Lucas", "Zoe", "Ethan", "Mia", "Benjamin", "Aiden", "Isabella",
    "Mason", "Harper", "Elijah", "Evelyn", "James", "Abigail", "William", "Emily",
    "Michael", "Elizabeth", "Daniel", "Mila", "Henry", "Ella", "Jackson", "Avery",
    "Sebastian", "Sofia", "Jack", "Camila", "Samuel", "Aria", "Owen", "Scarlett"
]

LAST_NAMES = [
    "Jenkins", "Chen", "Rostova", "Kim", "Diallo", "Santana", "Sharma", "O'Connor",
    "Hopper", "Sato", "Al-Mansoor", "Wright", "Dubois", "Fernandez", "Schmidt",
    "Mahmood", "Taylor", "Williams", "Martinez", "Silva", "Vanderberg", "Brown",
    "Johnson", "Lee", "Davis", "Miller", "Wilson", "Moore", "Anderson", "Thomas",
    "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Robinson", "Clark"
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ALLERGIES_LIST = ["None Known", "Penicillin", "Sulfa Drugs", "Aspirin", "Iodine Contrast", "Latex", "Codeine"]

CLINICAL_PROFILES = [
    {
        "condition": "Type-2 Diabetes",
        "icd10": "E11.9",
        "biomarker": "HbA1c",
        "unit": "%",
        "normal_range": (4.5, 6.4),
        "abnormal_range": (6.5, 11.5),
        "notes": "Patient reports polydipsia and fatigue. Initiated diet monitoring.",
        "medications": [
            {"drug": "Metformin", "dose": "1000mg BID", "freq": "Twice Daily", "eff_rate": 0.80},
            {"drug": "Empagliflozin", "dose": "25mg daily", "freq": "Once Daily", "eff_rate": 0.84},
            {"drug": "Semaglutide", "dose": "1.0mg weekly", "freq": "Weekly SubQ", "eff_rate": 0.89},
        ]
    },
    {
        "condition": "Essential Hypertension",
        "icd10": "I10",
        "biomarker": "Systolic BP",
        "unit": "mmHg",
        "normal_range": (110, 128),
        "abnormal_range": (132, 178),
        "notes": "Persistent elevation on automated cuff readings. Monitored for end-organ damage.",
        "medications": [
            {"drug": "Lisinopril", "dose": "20mg daily", "freq": "Once Daily", "eff_rate": 0.76},
            {"drug": "Amlodipine", "dose": "10mg daily", "freq": "Once Daily", "eff_rate": 0.79},
            {"drug": "Losartan", "dose": "50mg daily", "freq": "Once Daily", "eff_rate": 0.74},
        ]
    },
    {
        "condition": "Coronary Artery Disease",
        "icd10": "I25.1",
        "biomarker": "LDL-C",
        "unit": "mg/dL",
        "normal_range": (60, 99),
        "abnormal_range": (105, 210),
        "notes": "Mild exertional angina. Baseline echocardiogram within normal limits.",
        "medications": [
            {"drug": "Atorvastatin", "dose": "40mg daily", "freq": "Nightly", "eff_rate": 0.82},
            {"drug": "Clopidogrel", "dose": "75mg daily", "freq": "Once Daily", "eff_rate": 0.72},
        ]
    },
    {
        "condition": "Bronchial Asthma",
        "icd10": "J45.9",
        "biomarker": "FEV1/FVC",
        "unit": "%",
        "normal_range": (75, 88),
        "abnormal_range": (48, 68),
        "notes": "Nocturnal wheezing exacerbations during seasonal changes.",
        "medications": [
            {"drug": "Fluticasone", "dose": "220mcg BID", "freq": "Twice Daily Inhalation", "eff_rate": 0.81},
            {"drug": "Montelukast", "dose": "10mg daily", "freq": "Nightly", "eff_rate": 0.68},
        ]
    }
]

SEVERITIES = ["Mild", "Moderate", "Severe", "Critical"]

def create_hospital_schema(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        national_id TEXT UNIQUE NOT NULL,
        token TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        blood_group TEXT NOT NULL,
        allergies TEXT NOT NULL,
        primary_condition TEXT NOT NULL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS medical_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL,
        condition TEXT NOT NULL,
        icd10 TEXT NOT NULL,
        severity TEXT NOT NULL,
        diagnosis_year INTEGER NOT NULL,
        clinical_notes TEXT NOT NULL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS diagnostics (
        diagnostic_id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL,
        test_name TEXT NOT NULL,
        biomarker_name TEXT NOT NULL,
        biomarker_value REAL NOT NULL,
        unit TEXT NOT NULL,
        abnormal_flag INTEGER NOT NULL,
        test_year INTEGER NOT NULL
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL,
        medication TEXT NOT NULL,
        dosage TEXT NOT NULL,
        frequency TEXT NOT NULL,
        days_supply INTEGER NOT NULL,
        adherence_rate REAL NOT NULL,
        response_outcome TEXT NOT NULL
    );
    """)

def insert_full_record(conn: sqlite3.Connection, patient_data, history_data, diag_data, rx_data):
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO patients (national_id, token, name, age, gender, blood_group, allergies, primary_condition)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, patient_data)

    if history_data:
        cursor.execute("""
        INSERT INTO medical_history (token, condition, icd10, severity, diagnosis_year, clinical_notes)
        VALUES (?, ?, ?, ?, ?, ?);
        """, history_data)

    if diag_data:
        cursor.execute("""
        INSERT INTO diagnostics (token, test_name, biomarker_name, biomarker_value, unit, abnormal_flag, test_year)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, diag_data)

    if rx_data:
        cursor.execute("""
        INSERT INTO prescriptions (token, medication, dosage, frequency, days_supply, adherence_rate, response_outcome)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, rx_data)

def seed_databases(total_master_patients: int = 150, random_seed: int = 42):
    random.seed(random_seed)

    # Initialize federation DB for sharing requests and notifications
    init_federation_db()

    # Clean old files
    for p in [DB_A_PATH, DB_B_PATH, DB_C_PATH]:
        if p.exists():
            try:
                os.remove(p)
            except Exception:
                pass

    conn_a = sqlite3.connect(DB_A_PATH)
    conn_b = sqlite3.connect(DB_B_PATH)
    conn_c = sqlite3.connect(DB_C_PATH)

    create_hospital_schema(conn_a)
    create_hospital_schema(conn_b)
    create_hospital_schema(conn_c)

    # Generate master patients
    for i in range(1, total_master_patients + 1):
        nat_id = f"NAT-{10000 + i}"
        token = generate_blinded_token(nat_id)

        fn = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
        ln = LAST_NAMES[((i - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]
        name = f"{fn} {ln}"
        gender = "F" if (i % 2 == 1) else "M"

        age = random.randint(22, 82)
        blood = random.choice(BLOOD_GROUPS)
        allergy = random.choice(ALLERGIES_LIST)

        profile = random.choice(CLINICAL_PROFILES)
        condition = profile["condition"]
        icd10 = profile["icd10"]
        severity = random.choice(SEVERITIES)
        diag_year = random.randint(2020, 2025)

        # Diagnostics data
        is_abnormal = random.random() < 0.65
        val_range = profile["abnormal_range"] if is_abnormal else profile["normal_range"]
        biomarker_val = round(random.uniform(val_range[0], val_range[1]), 1)
        abnormal_flag = 1 if is_abnormal else 0

        # Prescription data
        med_choice = random.choice(profile["medications"])
        adherence = round(random.uniform(0.65, 0.98), 2)
        response = "Positive" if random.random() < med_choice["eff_rate"] else "Partial"

        patient_tuple = (nat_id, token, name, age, gender, blood, allergy, condition)
        history_tuple = (token, condition, icd10, severity, diag_year, profile["notes"])
        diag_tuple = (token, f"Comprehensive Panel ({condition})", profile["biomarker"], biomarker_val, profile["unit"], abnormal_flag, 2025)
        rx_tuple = (token, med_choice["drug"], med_choice["dose"], med_choice["freq"], 60, adherence, response)

        # Distribute based on user's scenario:
        # Group 1 (Patients 1 to 50): Visited Hospital A FIRST.
        # Has full records in Hospital A.
        # Zero records in Hospital B and C. When patient later walks into Hospital B,
        # Hospital B discovers data in Hospital A and initiates a scoped data request!
        if i <= 50:
            insert_full_record(conn_a, patient_tuple, history_tuple, diag_tuple, rx_tuple)

        # Group 2 (Patients 51 to 90): Visited Hospital B FIRST.
        # Has full records in Hospital B.
        elif i <= 90:
            insert_full_record(conn_b, patient_tuple, history_tuple, diag_tuple, rx_tuple)

        # Group 3 (Patients 91 to 125): Visited Hospital C FIRST.
        # Has full records in Hospital C.
        elif i <= 125:
            insert_full_record(conn_c, patient_tuple, history_tuple, diag_tuple, rx_tuple)

        # Group 4 (Patients 126 to 150): Multi-hospital visits (e.g. visited A for initial diagnosis, B for lab test)
        else:
            insert_full_record(conn_a, patient_tuple, history_tuple, None, rx_tuple)
            insert_full_record(conn_b, patient_tuple, None, diag_tuple, None)

    conn_a.commit()
    conn_b.commit()
    conn_c.commit()

    stats = {
        "hospital_a": conn_a.execute("SELECT count(*) FROM patients").fetchone()[0],
        "hospital_b": conn_b.execute("SELECT count(*) FROM patients").fetchone()[0],
        "hospital_c": conn_c.execute("SELECT count(*) FROM patients").fetchone()[0],
    }

    conn_a.close()
    conn_b.close()
    conn_c.close()

    print(f"[Multi-Hospital Seed Complete] Hospital A: {stats['hospital_a']} patients | Hospital B: {stats['hospital_b']} patients | Hospital C: {stats['hospital_c']} patients")
    return stats

if __name__ == "__main__":
    seed_databases()
