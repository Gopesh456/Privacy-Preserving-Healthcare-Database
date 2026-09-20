"""
Data Anonymization Engine: k-Anonymity and l-Diversity.
Transforms quasi-identifiers (e.g., Age, Gender) into generalized intervals,
and suppresses small outlier equivalence classes to guarantee k >= 5 and l >= 2.
Prevents identity linkage attacks on microdata releases.
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict

def generalize_age(age: int) -> str:
    """Generalizes exact age into 10-year demographic bands."""
    if age < 30:
        return "20-29"
    elif age < 40:
        return "30-39"
    elif age < 50:
        return "40-49"
    elif age < 60:
        return "50-59"
    elif age < 70:
        return "60-69"
    elif age < 80:
        return "70-79"
    else:
        return "80+"

class AnonymizationEngine:
    def __init__(self, k_threshold: int = 5, l_threshold: int = 2):
        self.k_threshold = k_threshold
        self.l_threshold = l_threshold

    def anonymize_cohort(
        self,
        records: List[Dict[str, Any]],
        quasi_identifiers: List[str] = ["age", "gender"],
        sensitive_attribute: str = "condition"
    ) -> Dict[str, Any]:
        """
        Applies generalization and suppression to ensure k-anonymity and l-diversity.
        """
        if not records:
            return {
                "anonymized_records": [],
                "total_input_records": 0,
                "suppressed_records": 0,
                "k_threshold": self.k_threshold,
                "l_threshold": self.l_threshold,
                "equivalence_classes": []
            }

        # Step 1: Generalize quasi-identifiers
        generalized_records = []
        for r in records:
            gen_r = dict(r)
            # Remove any direct identifiers or tokens
            gen_r.pop("token", None)
            gen_r.pop("patient_id", None)

            if "age" in gen_r:
                gen_r["age_group"] = generalize_age(gen_r["age"])
                del gen_r["age"]
            generalized_records.append(gen_r)

        # Step 2: Group into Equivalence Classes
        eq_classes = defaultdict(list)
        for r in generalized_records:
            eq_key = tuple(r.get(qi if qi != "age" else "age_group", "*") for qi in quasi_identifiers)
            eq_classes[eq_key].append(r)

        # Step 3: Evaluate k-anonymity and l-diversity & apply suppression
        anonymized_dataset = []
        suppressed_count = 0
        eq_class_reports = []

        for eq_key, class_records in eq_classes.items():
            class_size = len(class_records)
            # Check distinct sensitive values for l-diversity
            sensitive_values = set(r.get(sensitive_attribute) for r in class_records if sensitive_attribute in r)
            distinct_sensitive_count = len(sensitive_values)

            is_k_satisfied = class_size >= self.k_threshold
            is_l_satisfied = distinct_sensitive_count >= self.l_threshold

            if is_k_satisfied and is_l_satisfied:
                anonymized_dataset.extend(class_records)
                status = "Retained (k and l satisfied)"
            else:
                suppressed_count += class_size
                status = f"Suppressed (Size={class_size} < {self.k_threshold} or Diversity={distinct_sensitive_count} < {self.l_threshold})"

            eq_class_reports.append({
                "equivalence_class": dict(zip(quasi_identifiers, eq_key)),
                "class_size": class_size,
                "distinct_sensitive_values": distinct_sensitive_count,
                "status": status
            })

        return {
            "anonymized_records": anonymized_dataset,
            "total_input_records": len(records),
            "retained_records": len(anonymized_dataset),
            "suppressed_records": suppressed_count,
            "suppression_rate_percent": round((suppressed_count / len(records)) * 100, 1) if records else 0,
            "k_threshold": self.k_threshold,
            "l_threshold": self.l_threshold,
            "equivalence_classes": eq_class_reports
        }
