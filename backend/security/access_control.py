"""
Access Control Engine: Role-Based (RBAC) and Purpose-Based (PBAC) Access Control.
Enforces that queries are executed only by authenticated roles for legitimate, declared clinical purposes,
with appropriate privacy budgets and authorization constraints.
"""

from typing import Dict, Any, List, Optional

ROLES_PERMISSIONS = {
    "HOSPITAL_ADMIN": {
        "description": "Hospital Medical Administrator",
        "max_epsilon_per_query": 5.0,
        "allowed_purposes": ["CONTINUATION_OF_CARE", "EMERGENCY_TREATMENT", "SECOND_OPINION", "CLINICAL_RESEARCH", "TREATMENT_EFFICACY"],
        "can_anonymize_export": True,
        "can_view_audit": True,
        "can_request_data": True
    },
    "HOSPITAL_A_ADMIN": {
        "description": "Hospital A Medical Administrator",
        "max_epsilon_per_query": 5.0,
        "allowed_purposes": ["CONTINUATION_OF_CARE", "EMERGENCY_TREATMENT", "SECOND_OPINION", "CLINICAL_RESEARCH", "TREATMENT_EFFICACY"],
        "can_anonymize_export": True,
        "can_view_audit": True,
        "can_request_data": True
    },
    "HOSPITAL_B_ADMIN": {
        "description": "Hospital B Medical Administrator",
        "max_epsilon_per_query": 5.0,
        "allowed_purposes": ["CONTINUATION_OF_CARE", "EMERGENCY_TREATMENT", "SECOND_OPINION", "CLINICAL_RESEARCH", "TREATMENT_EFFICACY"],
        "can_anonymize_export": True,
        "can_view_audit": True,
        "can_request_data": True
    },
    "HOSPITAL_C_ADMIN": {
        "description": "Hospital C Medical Administrator",
        "max_epsilon_per_query": 5.0,
        "allowed_purposes": ["CONTINUATION_OF_CARE", "EMERGENCY_TREATMENT", "SECOND_OPINION", "CLINICAL_RESEARCH", "TREATMENT_EFFICACY"],
        "can_anonymize_export": True,
        "can_view_audit": True,
        "can_request_data": True
    },
    "CHIEF_MEDICAL_OFFICER": {
        "description": "Hospital Network Medical Director",
        "max_epsilon_per_query": 5.0,
        "allowed_purposes": ["CONTINUATION_OF_CARE", "EMERGENCY_TREATMENT", "SECOND_OPINION", "CLINICAL_RESEARCH", "TREATMENT_EFFICACY", "SAFETY_SURVEILLANCE", "EMERGENCY_EPIDEMIOLOGY"],
        "can_anonymize_export": True,
        "can_view_audit": True,
        "can_request_data": True
    },
    "CLINICAL_RESEARCHER": {
        "description": "Academic / Hospital Clinical Investigator",
        "max_epsilon_per_query": 2.5,
        "allowed_purposes": ["CLINICAL_RESEARCH", "TREATMENT_EFFICACY"],
        "can_anonymize_export": True,
        "can_view_audit": False,
        "can_request_data": False
    },
    "PHARMACOVIGILANCE_ANALYST": {
        "description": "Drug Safety and Post-Marketing Surveillance Specialist",
        "max_epsilon_per_query": 2.0,
        "allowed_purposes": ["SAFETY_SURVEILLANCE", "TREATMENT_EFFICACY"],
        "can_anonymize_export": False,
        "can_view_audit": False,
        "can_request_data": False
    },
    "EXTERNAL_AUDITOR": {
        "description": "HIPAA / GDPR Compliance & Ledger Auditor",
        "max_epsilon_per_query": 0.0,  # Cannot execute clinical queries
        "allowed_purposes": ["COMPLIANCE_AUDIT"],
        "can_anonymize_export": False,
        "can_view_audit": True,
        "can_request_data": False
    }
}

VALID_PURPOSES = [
    "CONTINUATION_OF_CARE",
    "EMERGENCY_TREATMENT",
    "SECOND_OPINION",
    "CLINICAL_RESEARCH",
    "TREATMENT_EFFICACY",
    "SAFETY_SURVEILLANCE",
    "EMERGENCY_EPIDEMIOLOGY",
    "COMPLIANCE_AUDIT"
]

class AccessControlPolicy:
    @staticmethod
    def validate_request(
        role: str,
        purpose: str,
        requested_epsilon: float = 1.0,
        is_export: bool = False
    ) -> Dict[str, Any]:
        """
        Validates whether the user's role and purpose satisfy the governance policy.
        """
        if role not in ROLES_PERMISSIONS:
            return {
                "authorized": False,
                "reason": f"Unknown or unauthorized role: '{role}'"
            }

        perms = ROLES_PERMISSIONS[role]

        if purpose not in VALID_PURPOSES:
            return {
                "authorized": False,
                "reason": f"Invalid purpose declaration: '{purpose}'"
            }

        if purpose not in perms["allowed_purposes"]:
            return {
                "authorized": False,
                "reason": f"Role '{role}' is not authorized for purpose '{purpose}'"
            }

        if role == "EXTERNAL_AUDITOR" and not is_export and requested_epsilon > 0:
            return {
                "authorized": False,
                "reason": "Auditor role has strictly read-only access to audit logs and cannot run patient queries."
            }

        if requested_epsilon > perms["max_epsilon_per_query"]:
            return {
                "authorized": False,
                "reason": f"Requested ε={requested_epsilon} exceeds role maximum allowance of ε={perms['max_epsilon_per_query']}."
            }

        if is_export and not perms["can_anonymize_export"]:
            return {
                "authorized": False,
                "reason": f"Role '{role}' is not permitted to request cohort microdata exports."
            }

        return {
            "authorized": True,
            "role": role,
            "purpose": purpose,
            "permissions": perms
        }
