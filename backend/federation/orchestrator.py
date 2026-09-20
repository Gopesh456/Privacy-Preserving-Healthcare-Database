"""
Federated Query Orchestrator.
Coordinates the Defense-in-Depth Privacy Pipeline across:
- Hospital A (Medical History)
- Hospital B (Diagnostics & Labs)
- Hospital C (Pharmacy & Prescriptions)
Integrates PBAC Access Control, Blinded Token Linkage, SMPC Secret Sharing,
Differential Privacy (Laplace/Gaussian), and the Cryptographic Audit Ledger.
"""

from typing import Dict, Any, Optional, List
from backend.database.hospital_nodes import HospitalANode, HospitalBNode, HospitalCNode
from backend.privacy.differential_privacy import (
    DifferentialPrivacyEngine,
    PrivacyBudgetExhaustedError,
    SmallCohortSuppressionError
)
from backend.privacy.smpc import SMPCSecureAggregator
from backend.privacy.anonymizer import AnonymizationEngine
from backend.security.access_control import AccessControlPolicy
from backend.security.audit_ledger import AuditLedger

class FederatedOrchestrator:
    def __init__(self, total_epsilon_budget: float = 10.0):
        self.node_a = HospitalANode()
        self.node_b = HospitalBNode()
        self.node_c = HospitalCNode()

        self.dp_engine = DifferentialPrivacyEngine(total_epsilon_budget=total_epsilon_budget)
        self.smpc = SMPCSecureAggregator()
        self.anonymizer = AnonymizationEngine(k_threshold=5, l_threshold=2)
        self.audit_ledger = AuditLedger()

    def get_nodes_info(self) -> List[Dict[str, Any]]:
        return [
            self.node_a.get_stats(),
            self.node_b.get_stats(),
            self.node_c.get_stats()
        ]

    def execute_collaborative_query(
        self,
        # Query filters
        condition: Optional[str] = None,
        severity: Optional[str] = None,
        biomarker: Optional[str] = None,
        abnormal_lab_only: bool = False,
        biomarker_max: Optional[float] = None,
        biomarker_min: Optional[float] = None,
        medication: Optional[str] = None,
        response_outcome: Optional[str] = None,
        min_adherence: Optional[float] = None,
        # Privacy & Security configuration
        epsilon: float = 1.0,
        use_dp: bool = True,
        use_smpc: bool = True,
        role: str = "CLINICAL_RESEARCHER",
        purpose: str = "CLINICAL_RESEARCH",
        researcher_name: str = "Dr. Clinical Investigator",
        enforce_suppression: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a distributed healthcare query across Hospital A, B, and C.
        """
        query_summary = (
            f"Query [Condition: {condition or 'Any'}, "
            f"Biomarker: {biomarker or 'Any'}, "
            f"Medication: {medication or 'Any'}, "
            f"Outcome: {response_outcome or 'Any'}]"
        )

        # 1. PBAC Access Control Check
        auth_result = AccessControlPolicy.validate_request(
            role=role,
            purpose=purpose,
            requested_epsilon=epsilon if use_dp else 0.0,
            is_export=False
        )
        if not auth_result["authorized"]:
            return {
                "success": False,
                "error_type": "ACCESS_DENIED",
                "error": auth_result["reason"]
            }

        # 2. Privacy Budget Check
        if use_dp:
            try:
                self.dp_engine.check_and_deduct_budget(epsilon, query_summary)
            except PrivacyBudgetExhaustedError as e:
                return {
                    "success": False,
                    "error_type": "BUDGET_EXHAUSTED",
                    "error": str(e),
                    "budget_status": self.dp_engine.get_budget_status()
                }

        # 3. Federated Sub-Query Dispatch (Each node evaluates inside its local enclave)
        # Hospital A: Finds matching blinded tokens based on Medical History
        tokens_a = self.node_a.query_matching_tokens(condition=condition, severity=severity)
        set_a = set(tokens_a)

        # Hospital B: Evaluates Diagnostic Reports
        # Only evaluates if biomarker criteria are provided; otherwise matches all candidate tokens
        if biomarker or abnormal_lab_only or biomarker_max is not None or biomarker_min is not None:
            tokens_b = self.node_b.query_matching_tokens(
                candidate_tokens=list(set_a),
                biomarker=biomarker,
                abnormal_only=abnormal_lab_only,
                max_value=biomarker_max,
                min_value=biomarker_min
            )
            set_ab = set_a.intersection(tokens_b)
        else:
            set_ab = set_a

        # Hospital C: Evaluates Prescriptions and Outcomes
        if medication or response_outcome or min_adherence is not None:
            tokens_c = self.node_c.query_matching_tokens(
                candidate_tokens=list(set_ab),
                medication=medication,
                response_outcome=response_outcome,
                min_adherence=min_adherence
            )
            final_tokens = set_ab.intersection(tokens_c)
        else:
            final_tokens = set_ab

        true_count = len(final_tokens)

        # 4. Secure Multi-Party Computation (SMPC) Simulation
        # Demonstrates additive secret sharing among nodes to sum cross-node cohort segments
        smpc_result = None
        if use_smpc:
            # Simulate each hospital's local partitioned contribution
            # e.g., cohort count split across participating regional facilities
            part_a = true_count // 3
            part_b = true_count // 3
            part_c = true_count - (part_a + part_b)
            node_shares_input = {
                "Hospital_A": part_a,
                "Hospital_B": part_b,
                "Hospital_C": part_c
            }
            smpc_result = self.smpc.run_secure_sum(node_shares_input)

        # 5. Differential Privacy Perturbation
        dp_result = None
        if use_dp:
            try:
                dp_result = self.dp_engine.laplace_mechanism(
                    true_value=float(true_count),
                    epsilon=epsilon,
                    sensitivity=1.0,
                    enforce_suppression=enforce_suppression
                )
            except SmallCohortSuppressionError as e:
                return {
                    "success": False,
                    "error_type": "COHORT_SUPPRESSED",
                    "error": str(e),
                    "true_count_suppressed": True,
                    "budget_status": self.dp_engine.get_budget_status()
                }

        # 6. Cryptographic Audit Ledger Recording
        participating = ["Hospital A (EHR)"]
        if biomarker or abnormal_lab_only or biomarker_max is not None:
            participating.append("Hospital B (Labs)")
        if medication or response_outcome or min_adherence is not None:
            participating.append("Hospital C (Pharmacy)")

        spent_epsilon = epsilon if use_dp else 0.0
        audit_block = self.audit_ledger.log_query(
            researcher=researcher_name,
            role=role,
            purpose=purpose,
            query_type="FEDERATED_COHORT_QUERY",
            query_parameters={
                "condition": condition,
                "severity": severity,
                "biomarker": biomarker,
                "medication": medication,
                "response_outcome": response_outcome,
                "epsilon": epsilon if use_dp else None,
                "use_smpc": use_smpc,
                "use_dp": use_dp
            },
            participating_nodes=participating,
            epsilon_spent=spent_epsilon
        )

        return {
            "success": True,
            "query_summary": query_summary,
            "result": {
                "reported_count": dp_result["perturbed_value"] if use_dp else true_count,
                "true_count": true_count,  # Provided for demonstration comparison
                "differential_privacy": dp_result,
                "smpc": smpc_result,
                "node_evaluations": {
                    "hospital_a_matched": len(set_a),
                    "hospital_b_filtered": len(set_ab),
                    "hospital_c_final": true_count
                }
            },
            "privacy_mode": {
                "differential_privacy_enabled": use_dp,
                "smpc_enabled": use_smpc,
                "epsilon_applied": epsilon if use_dp else 0.0
            },
            "budget_status": self.dp_engine.get_budget_status(),
            "audit_entry": {
                "block_index": audit_block.index,
                "block_hash": audit_block.block_hash,
                "timestamp": audit_block.timestamp
            }
        }

    def export_anonymized_microdata(
        self,
        condition: Optional[str] = None,
        role: str = "CLINICAL_RESEARCHER",
        purpose: str = "CLINICAL_RESEARCH",
        researcher_name: str = "Dr. Clinical Investigator",
        k: int = 5,
        l: int = 2
    ) -> Dict[str, Any]:
        """
        Exports a k-anonymized cohort dataset with quasi-identifier generalization
        and small-class suppression.
        """
        auth_result = AccessControlPolicy.validate_request(
            role=role,
            purpose=purpose,
            requested_epsilon=0.0,
            is_export=True
        )
        if not auth_result["authorized"]:
            return {"success": False, "error": auth_result["reason"]}

        # Query tokens from Hospital A
        tokens = self.node_a.query_matching_tokens(condition=condition)
        if not tokens:
            return {"success": False, "error": "No patient records match the specified criteria."}

        # Retrieve attributes from Hospital A and Hospital C for matched tokens
        records_a = self.node_a.get_cohort_attributes(tokens)
        prescriptions_c = {p["token"]: p for p in self.node_c.get_cohort_prescriptions(tokens)}

        # Merge in memory purely for anonymizer pipeline
        merged_raw = []
        for r in records_a:
            tok = r["token"]
            rx = prescriptions_c.get(tok, {})
            merged_raw.append({
                "age": r["age"],
                "gender": r["gender"],
                "condition": r["condition"],
                "severity": r["severity"],
                "medication": rx.get("medication", "None"),
                "outcome": rx.get("response_outcome", "Unknown")
            })

        self.anonymizer.k_threshold = k
        self.anonymizer.l_threshold = l
        anonymized_result = self.anonymizer.anonymize_cohort(
            records=merged_raw,
            quasi_identifiers=["age", "gender"],
            sensitive_attribute="outcome"
        )

        # Log audit entry
        self.audit_ledger.log_query(
            researcher=researcher_name,
            role=role,
            purpose=purpose,
            query_type="K_ANONYMITY_MICRODATA_EXPORT",
            query_parameters={"condition": condition, "k": k, "l": l},
            participating_nodes=["Hospital A", "Hospital C"],
            epsilon_spent=0.0
        )

        return {
            "success": True,
            "anonymization_summary": anonymized_result,
            "sample_records": anonymized_result["anonymized_records"][:25]
        }
