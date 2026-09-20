"""
Federated Query Orchestrator & Inter-Hospital Exchange Hub.
Coordinates:
1. Privacy-Preserving Patient Discovery across independent hospital nodes.
2. Inter-hospital Data Sharing Requests with review & verification workflow.
3. Defense-in-Depth statistical queries with Differential Privacy and SMPC.
4. Tamper-evident Audit Ledger tracking for all queries and sharing events.
"""

from typing import Dict, Any, Optional, List
from backend.database.hospital_nodes import (
    HospitalNode,
    hospital_a_node,
    hospital_b_node,
    hospital_c_node,
    get_hospital_node
)
from backend.database.federation_db import FederationCoordinator
from backend.database.tokens import generate_blinded_token
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
        self.node_a = hospital_a_node
        self.node_b = hospital_b_node
        self.node_c = hospital_c_node

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

    # =========================================================================
    # Patient Discovery & Zero-Knowledge Presence Locator
    # =========================================================================
    def discover_patient(self, current_hospital_id: str, query: str) -> Dict[str, Any]:
        """
        Searches for a patient:
        1. Checks current hospital's local database.
        2. If not found locally (or to check federation availability), queries peer
           hospitals via blinded tokens.
        3. Returns a privacy-preserving presence report without leaking clinical contents.
        """
        current_node = get_hospital_node(current_hospital_id) or self.node_a
        all_nodes = [self.node_a, self.node_b, self.node_c]

        # 1. Search locally
        local_matches = current_node.search_local_patients(query)
        target_token = None
        target_name = None

        if local_matches:
            target_token = local_matches[0]["token"]
            target_name = local_matches[0]["name"]
            local_profile = current_node.get_patient_full_profile(target_token)
            local_present = True
        else:
            # If query is a national ID or token directly, or search across peer names
            if query.startswith("pt_"):
                target_token = query
            elif query.upper().startswith("NAT-"):
                target_token = generate_blinded_token(query.upper())
            else:
                # Blind lookup helper: find matching token from any node for demonstration
                for node in all_nodes:
                    peer_matches = node.search_local_patients(query)
                    if peer_matches:
                        target_token = peer_matches[0]["token"]
                        target_name = peer_matches[0]["name"]
                        break

            local_profile = None
            local_present = False

        if not target_token:
            return {
                "search_query": query,
                "found_anywhere": False,
                "message": f"No patient records matching '{query}' found anywhere in the hospital network."
            }

        # 2. Query presence at all nodes
        peer_presence = []
        for node in all_nodes:
            presence_info = node.check_patient_presence(target_token)
            is_local = (node.node_id == current_hospital_id)
            peer_presence.append({
                "hospital_id": node.node_id,
                "hospital_name": node.name,
                "is_current_hospital": is_local,
                "present": presence_info["present"],
                "categories": presence_info["categories"],
                "patient_name_masked": presence_info["patient_name_masked"] or (target_name if is_local else None),
                "can_request": (not is_local and presence_info["present"])
            })

        found_anywhere = any(p["present"] for p in peer_presence)

        return {
            "search_query": query,
            "patient_token": target_token,
            "patient_name": target_name,
            "local_present": local_present,
            "local_profile": local_profile,
            "found_anywhere": found_anywhere,
            "federation_presence": peer_presence
        }

    # =========================================================================
    # Granular Inter-Hospital Data Sharing & Verification
    # =========================================================================
    def request_patient_data(
        self,
        from_hospital: str,
        to_hospital: str,
        patient_token: str,
        patient_name: str,
        requested_categories: List[str],
        purpose: str,
        justification: str,
        requester_role: str = "HOSPITAL_ADMIN"
    ) -> Dict[str, Any]:
        """
        Hospital B submits a scoped request to Hospital A for specific patient data.
        """
        # Validate purpose and permissions
        auth = AccessControlPolicy.validate_request(
            role=requester_role,
            purpose=purpose,
            requested_epsilon=0.0
        )
        if not auth["authorized"]:
            return {"success": False, "error": auth["reason"]}

        if not requested_categories:
            return {"success": False, "error": "At least one data category must be selected."}

        res = FederationCoordinator.create_request(
            from_hospital=from_hospital,
            to_hospital=to_hospital,
            patient_token=patient_token,
            patient_name=patient_name,
            requested_categories=requested_categories,
            purpose=purpose,
            justification=justification
        )

        # Log in audit ledger
        self.audit_ledger.log_query(
            researcher=f"Admin ({from_hospital.upper()})",
            role=requester_role,
            purpose=purpose,
            query_type="INTER_HOSPITAL_DATA_REQUESTED",
            query_parameters={
                "request_id": res["request_id"],
                "from_hospital": from_hospital,
                "to_hospital": to_hospital,
                "patient_token": patient_token,
                "categories": requested_categories,
                "justification": justification
            },
            participating_nodes=[from_hospital, to_hospital],
            epsilon_spent=0.0
        )

        return res

    def review_patient_data_request(
        self,
        request_id: str,
        reviewer_hospital: str,
        reviewer_name: str,
        decision: str,  # 'APPROVED' or 'REJECTED'
        approved_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Target Hospital Admin reviews, verifies, and approves/rejects sharing.
        Only the verified and approved categories are extracted.
        """
        extracted_payload = None
        target_node = get_hospital_node(reviewer_hospital)

        if decision == "APPROVED":
            if not approved_categories:
                return {"success": False, "error": "At least one category must be approved for release."}

            # Retrieve request from DB to get patient token
            requests = FederationCoordinator.get_requests_for_hospital(reviewer_hospital)
            target_req = next((r for r in requests["incoming"] if r["request_id"] == request_id), None)
            if not target_req:
                return {"success": False, "error": "Request not found in incoming queue."}

            token = target_req["patient_token"]
            extracted_payload = target_node.extract_scoped_records(token, approved_categories)

        review_res = FederationCoordinator.review_request(
            request_id=request_id,
            reviewer_hospital=reviewer_hospital,
            reviewer_name=reviewer_name,
            decision=decision,
            approved_categories=approved_categories,
            extracted_payload=extracted_payload
        )

        # Log review in audit ledger
        self.audit_ledger.log_query(
            researcher=reviewer_name,
            role=f"{reviewer_hospital.upper()}_ADMIN",
            purpose="DATA_SHARING_VERIFICATION",
            query_type="DATA_SHARING_APPROVED" if decision == "APPROVED" else "DATA_SHARING_REJECTED",
            query_parameters={
                "request_id": request_id,
                "decision": decision,
                "approved_categories": approved_categories or []
            },
            participating_nodes=[reviewer_hospital],
            epsilon_spent=0.0
        )

        return review_res

    # =========================================================================
    # Statistical Federated Queries (SMPC + Differential Privacy)
    # =========================================================================
    def execute_collaborative_query(
        self,
        condition: Optional[str] = None,
        severity: Optional[str] = None,
        biomarker: Optional[str] = None,
        abnormal_lab_only: bool = False,
        biomarker_max: Optional[float] = None,
        biomarker_min: Optional[float] = None,
        medication: Optional[str] = None,
        response_outcome: Optional[str] = None,
        min_adherence: Optional[float] = None,
        epsilon: float = 1.0,
        use_dp: bool = True,
        use_smpc: bool = True,
        role: str = "CLINICAL_RESEARCHER",
        purpose: str = "CLINICAL_RESEARCH",
        researcher_name: str = "Dr. Clinical Investigator",
        enforce_suppression: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a privacy-preserving statistical query across the hospital nodes.
        """
        query_summary = (
            f"Federated Query [Condition: {condition or 'Any'}, "
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

        # 3. Federated Local Evaluations across all three hospitals
        matched_tokens = set()
        hospital_matches = {}

        for node in [self.node_a, self.node_b, self.node_c]:
            with node.get_connection() as conn:
                cursor = conn.cursor()
                # Query matching tokens across local clinical tables
                sql = """
                SELECT DISTINCT p.token
                FROM patients p
                LEFT JOIN medical_history m ON p.token = m.token
                LEFT JOIN diagnostics d ON p.token = d.token
                LEFT JOIN prescriptions r ON p.token = r.token
                WHERE 1=1
                """
                params = []
                if condition:
                    sql += " AND (p.primary_condition = ? OR m.condition = ?)"
                    params.extend([condition, condition])
                if severity:
                    sql += " AND m.severity = ?"
                    params.append(severity)
                if biomarker:
                    sql += " AND d.biomarker_name = ?"
                    params.append(biomarker)
                if abnormal_lab_only:
                    sql += " AND d.abnormal_flag = 1"
                if medication:
                    sql += " AND r.medication = ?"
                    params.append(medication)
                if response_outcome:
                    sql += " AND r.response_outcome = ?"
                    params.append(response_outcome)

                node_tokens = [r[0] for r in cursor.execute(sql, params).fetchall()]
                hospital_matches[node.name] = len(node_tokens)
                matched_tokens.update(node_tokens)

        true_count = len(matched_tokens)

        # 4. SMPC Simulation
        smpc_result = None
        if use_smpc:
            smpc_inputs = {
                "Hospital_A": hospital_matches.get(self.node_a.name, 0),
                "Hospital_B": hospital_matches.get(self.node_b.name, 0),
                "Hospital_C": hospital_matches.get(self.node_c.name, 0)
            }
            smpc_result = self.smpc.run_secure_sum(smpc_inputs)

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

        # 6. Cryptographic Audit Recording
        audit_block = self.audit_ledger.log_query(
            researcher=researcher_name,
            role=role,
            purpose=purpose,
            query_type="FEDERATED_COHORT_QUERY",
            query_parameters={
                "condition": condition,
                "biomarker": biomarker,
                "medication": medication,
                "response_outcome": response_outcome,
                "epsilon": epsilon if use_dp else None,
                "use_smpc": use_smpc,
                "use_dp": use_dp
            },
            participating_nodes=["Hospital A", "Hospital B", "Hospital C"],
            epsilon_spent=epsilon if use_dp else 0.0
        )

        return {
            "success": True,
            "query_summary": query_summary,
            "result": {
                "reported_count": dp_result["perturbed_value"] if use_dp else true_count,
                "true_count": true_count,
                "differential_privacy": dp_result,
                "smpc": smpc_result,
                "node_evaluations": {
                    "hospital_a_matched": hospital_matches.get(self.node_a.name, 0),
                    "hospital_b_filtered": hospital_matches.get(self.node_b.name, 0),
                    "hospital_c_final": hospital_matches.get(self.node_c.name, 0)
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
        merged_raw = []
        for node in [self.node_a, self.node_b, self.node_c]:
            with node.get_connection() as conn:
                cursor = conn.cursor()
                query_sql = """
                SELECT p.age, p.gender, p.primary_condition as condition,
                       COALESCE(m.severity, 'Moderate') as severity,
                       COALESCE(r.medication, 'None') as medication,
                       COALESCE(r.response_outcome, 'Unknown') as outcome
                FROM patients p
                LEFT JOIN medical_history m ON p.token = m.token
                LEFT JOIN prescriptions r ON p.token = r.token
                WHERE 1=1
                """
                params = []
                if condition:
                    query_sql += " AND p.primary_condition = ?"
                    params.append(condition)
                rows = cursor.execute(query_sql, params).fetchall()
                merged_raw.extend([dict(r) for r in rows])

        self.anonymizer.k_threshold = k
        self.anonymizer.l_threshold = l
        anonymized_result = self.anonymizer.anonymize_cohort(
            records=merged_raw,
            quasi_identifiers=["age", "gender"],
            sensitive_attribute="outcome"
        )

        self.audit_ledger.log_query(
            researcher=researcher_name,
            role=role,
            purpose=purpose,
            query_type="K_ANONYMITY_MICRODATA_EXPORT",
            query_parameters={"condition": condition, "k": k, "l": l},
            participating_nodes=["Hospital A", "Hospital B", "Hospital C"],
            epsilon_spent=0.0
        )

        return {
            "success": True,
            "anonymization_summary": anonymized_result,
            "sample_records": anonymized_result["anonymized_records"][:25]
        }
