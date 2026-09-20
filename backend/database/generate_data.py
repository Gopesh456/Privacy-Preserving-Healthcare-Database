"""
Synthetic Healthcare Database Generator for Federated Hospital Nodes.
Generates realistic, clinical data partitioned across:
- Hospital A: Medical History (Demographics, Conditions, ICD-10, Severity, Onset)
- Hospital B: Diagnostics & Lab Reports (Biomarkers, Lab Values, Normal/Abnormal Flags)
- Hospital C: Pharmacy & Prescriptions (Medications, Dosages, Adherence, Response Outcomes)

Uses deterministic pseudonym tokens to simulate Private Entity Linkage.
"""

import sqlite3
import random
import os
from pathlib import Path
from backend.database.tokens import generate_blinded_token

DB_DIR = Path(__file__).parent
DB_A_PATH = DB_DIR / "hospital_a.db"
DB_B_PATH = DB_DIR / "hospital_b.db"
DB_C_PATH = DB_DIR / "hospital_c.db"

# Master Clinical Definitions
CLINICAL_PROFILES = [
    {
        "condition": "Type-2 Diabetes",
        "icd10": "E11.9",
        "biomarker": "HbA1c",
        "unit": "%",
        "normal_range": (4.5, 6.4),
        "abnormal_range": (6.5, 11.8),
        "medications": [
            {"drug": "Metformin", "dose": "1000mg BID", "eff_rate": 0.76},
            {"drug": "Empagliflozin", "dose": "25mg daily", "eff_rate": 0.82},
            {"drug": "Semaglutide", "dose": "1.0mg weekly", "eff_rate": 0.89},
        ]
    },
    {
        "condition": "Essential Hypertension",
        "icd10": "I10",
        "biomarker": "Systolic BP",
        "unit": "mmHg",
        "normal_range": (110, 128),
        "abnormal_range": (132, 185),
        "medications": [
            {"drug": "Lisinopril", "dose": "20mg daily", "eff_rate": 0.74},
            {"drug": "Amlodipine", "dose": "10mg daily", "eff_rate": 0.78},
            {"drug": "Losartan", "dose": "50mg daily", "eff_rate": 0.72},
        ]
    },
    {
        "condition": "Coronary Artery Disease",
        "icd10": "I25.1",
        "biomarker": "LDL-C",
        "unit": "mg/dL",
        "normal_range": (60, 99),
        "abnormal_range": (105, 230),
        "medications": [
            {"drug": "Atorvastatin", "dose": "40mg daily", "eff_rate": 0.81},
            {"drug": "Rosuvastatin", "dose": "20mg daily", "eff_rate": 0.85},
            {"drug": "Clopidogrel", "dose": "75mg daily", "eff_rate": 0.70},
        ]
    },
    {
        "condition": "Bronchial Asthma",
        "icd10": "J45.9",
        "biomarker": "FEV1/FVC",
        "unit": "%",
        "normal_range": (75, 88),
        "abnormal_range": (45, 69),
        "medications": [
            {"drug": "Fluticasone", "dose": "220mcg BID", "eff_rate": 0.80},
            {"drug": "Budesonide", "dose": "160mcg BID", "eff_rate": 0.78},
            {"drug": "Montelukast", "dose": "10mg daily", "eff_rate": 0.65},
        ]
    },
    {
        "condition": "Major Depressive Disorder",
        "icd10": "F32.9",
        "biomarker": "PHQ-9 Score",
        "unit": "pts",
        "normal_range": (1, 9),
        "abnormal_range": (10, 26),
        "medications": [
            {"drug": "Sertraline", "dose": "50mg daily", "eff_rate": 0.68},
            {"drug": "Escitalopram", "dose": "10mg daily", "eff_rate": 0.73},
            {"drug": "Duloxetine", "dose": "60mg daily", "eff_rate": 0.71},
        ]
    },
    {
        "condition": "Rheumatoid Arthritis",
        "icd10": "M06.9",
        "biomarker": "hs-CRP",
        "unit": "mg/L",
        "normal_range": (0.2, 2.8),
        "abnormal_range": (3.5, 28.0),
        "medications": [
            {"drug": "Methotrexate", "dose": "15mg weekly", "eff_rate": 0.67},
            {"drug": "Adalimumab", "dose": "40mg biweekly", "eff_rate": 0.84},
            {"drug": "Hydroxychloroquine", "dose": "200mg daily", "eff_rate": 0.60},
        ]
    }
]

SEVERITIES = ["Mild", "Moderate", "Severe", "Critical"]
GENDERS = ["M", "F"]

def seed_databases(total_patients: int = 600, random_seed: int = 42):
    random.seed(random_seed)

    # Clean old files if present
    for p in [DB_A_PATH, DB_B_PATH, DB_C_PATH]:
        if p.exists():
            os.remove(p)

    conn_a = sqlite3.connect(DB_A_PATH)
    conn_b = sqlite3.connect(DB_B_PATH)
    conn_c = sqlite3.connect(DB_C_PATH)

    # Create Tables
    # Hospital A: Medical History
    conn_a.execute("""
    CREATE TABLE patients (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        condition TEXT NOT NULL,
        icd10 TEXT NOT NULL,
        severity TEXT NOT NULL,
        diagnosis_year INTEGER NOT NULL
    );
    """)

    # Hospital B: Diagnostics & Lab Reports
    conn_b.execute("""
    CREATE TABLE diagnostics (
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

    # Hospital C: Pharmacy & Prescriptions
    conn_c.execute("""
    CREATE TABLE prescriptions (
        prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL,
        medication TEXT NOT NULL,
        dosage TEXT NOT NULL,
        days_supply INTEGER NOT NULL,
        adherence_rate REAL NOT NULL,
        response_outcome TEXT NOT NULL,
        adverse_event INTEGER NOT NULL
    );
    """)

    # Generate patient records
    patients_a = []
    diagnostics_b = []
    prescriptions_c = []

    for i in range(1, total_patients + 1):
        national_id = f"NAT-{100000 + i}"
        token = generate_blinded_token(national_id)

        # Primary condition
        profile = random.choice(CLINICAL_PROFILES)
        age = random.randint(22, 84)
        gender = random.choice(GENDERS)
        severity = random.choices(SEVERITIES, weights=[0.35, 0.40, 0.20, 0.05])[0]
        diagnosis_year = random.randint(2018, 2025)

        # Hospital A record
        patients_a.append((token, age, gender, profile["condition"], profile["icd10"], severity, diagnosis_year))

        # Hospital B diagnostics: 90% of patients have diagnostic records at Hospital B
        if random.random() < 0.92:
            is_abnormal = random.random() < 0.70
            val_range = profile["abnormal_range"] if is_abnormal else profile["normal_range"]
            biomarker_val = round(random.uniform(val_range[0], val_range[1]), 1)
            abnormal_flag = 1 if is_abnormal else 0
            test_year = random.randint(diagnosis_year, 2026)
            diagnostics_b.append((
                token,
                f"Panel for {profile['condition']}",
                profile["biomarker"],
                biomarker_val,
                profile["unit"],
                abnormal_flag,
                test_year
            ))

        # Hospital C prescriptions: 88% of patients have pharmacy records at Hospital C
        if random.random() < 0.90:
            med_choice = random.choice(profile["medications"])
            adherence = round(random.uniform(0.55, 0.99), 2)
            # Response outcome depends on efficacy rate and adherence
            success_prob = med_choice["eff_rate"] * (0.8 + 0.2 * adherence)
            roll = random.random()
            if roll < success_prob:
                response = "Positive"
                adverse = 0
            elif roll < success_prob + 0.18:
                response = "Partial"
                adverse = 0
            elif roll < success_prob + 0.23:
                response = "Adverse Event"
                adverse = 1
            else:
                response = "Non-Responsive"
                adverse = 0

            days = random.choice([30, 60, 90, 180])
            prescriptions_c.append((
                token,
                med_choice["drug"],
                med_choice["dose"],
                days,
                adherence,
                response,
                adverse
            ))

    # Bulk insert
    conn_a.executemany("""
    INSERT INTO patients (token, age, gender, condition, icd10, severity, diagnosis_year)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, patients_a)

    conn_b.executemany("""
    INSERT INTO diagnostics (token, test_name, biomarker_name, biomarker_value, unit, abnormal_flag, test_year)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, diagnostics_b)

    conn_c.executemany("""
    INSERT INTO prescriptions (token, medication, dosage, days_supply, adherence_rate, response_outcome, adverse_event)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, prescriptions_c)

    conn_a.commit()
    conn_b.commit()
    conn_c.commit()

    count_a = conn_a.execute("SELECT count(*) FROM patients").fetchone()[0]
    count_b = conn_b.execute("SELECT count(*) FROM diagnostics").fetchone()[0]
    count_c = conn_c.execute("SELECT count(*) FROM prescriptions").fetchone()[0]

    conn_a.close()
    conn_b.close()
    conn_c.close()

    print(f"[Seed Complete] Hospital A: {count_a} records | Hospital B: {count_b} records | Hospital C: {count_c} records")
    return {"hospital_a": count_a, "hospital_b": count_b, "hospital_c": count_c}

if __name__ == "__main__":
    seed_databases()
