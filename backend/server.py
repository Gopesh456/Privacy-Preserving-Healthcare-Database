"""
Backend API Server for Privacy-Preserving Healthcare Database.
Serves REST APIs for:
- Hospital Admin Authentication (Hospital A, B, C)
- Local Patient Record Management (EHR, Labs, Prescriptions)
- Privacy-Preserving Inter-Hospital Discovery & Availability
- Granular Scoped Sharing Requests, Review, and Verification
- Top-bar Real-Time Notifications
- Federated Statistical DP & SMPC Analytics
"""

import json
from pathlib import Path
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from backend.federation.orchestrator import FederatedOrchestrator
from backend.database.hospital_nodes import get_hospital_node
from backend.database.federation_db import FederationCoordinator
from backend.database.tokens import generate_blinded_token

orchestrator = FederatedOrchestrator(total_epsilon_budget=10.0)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# =========================================================================
# Authentication & Hospital Session Endpoints
# =========================================================================
async def auth_login(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = FederationCoordinator.authenticate(username, password)
    if not user:
        return JSONResponse({"success": False, "error": "Invalid hospital admin credentials."}, status_code=401)

    return JSONResponse({"success": True, "user": user})

# =========================================================================
# Local Patient Management Endpoints
# =========================================================================
async def search_local_patients(request):
    hospital_id = request.query_params.get("hospital_id", "node_a")
    q = request.query_params.get("q", "")
    node = get_hospital_node(hospital_id)
    if not node:
        return JSONResponse({"success": False, "error": "Unknown hospital node."}, status_code=404)

    patients = node.search_local_patients(q)
    return JSONResponse({"success": True, "hospital_id": hospital_id, "patients": patients})

async def get_patient_profile(request):
    hospital_id = request.query_params.get("hospital_id", "node_a")
    token = request.query_params.get("token", "")
    node = get_hospital_node(hospital_id)
    if not node:
        return JSONResponse({"success": False, "error": "Unknown hospital node."}, status_code=404)

    profile = node.get_patient_full_profile(token)
    if not profile:
        return JSONResponse({"success": False, "error": "Patient profile not found in local database."}, status_code=404)

    return JSONResponse({"success": True, "profile": profile})

async def add_new_patient(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    hospital_id = data.get("hospital_id", "node_a")
    node = get_hospital_node(hospital_id)
    if not node:
        return JSONResponse({"success": False, "error": "Unknown hospital node."}, status_code=404)

    nat_id = data.get("national_id", "")
    if not nat_id:
        return JSONResponse({"success": False, "error": "National ID / MRN is required."}, status_code=400)

    token = generate_blinded_token(nat_id)
    patient_record = {
        "national_id": nat_id,
        "token": token,
        "name": data.get("name", "Unknown"),
        "age": int(data.get("age", 30)),
        "gender": data.get("gender", "Other"),
        "blood_group": data.get("blood_group", "Unknown"),
        "allergies": data.get("allergies", "None Known"),
        "primary_condition": data.get("primary_condition", "Under Evaluation")
    }

    res = node.register_patient(patient_record)
    return JSONResponse({"success": True, "token": token, "patient_id": res["patient_id"]})

async def add_clinical_encounter(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    hospital_id = data.get("hospital_id", "node_a")
    category = data.get("category", "")
    token = data.get("token", "")
    payload = data.get("encounter_data", {})

    node = get_hospital_node(hospital_id)
    if not node:
        return JSONResponse({"success": False, "error": "Unknown hospital node."}, status_code=404)

    res = node.add_clinical_encounter(category, token, payload)
    return JSONResponse(res)

# =========================================================================
# Privacy-Preserving Discovery & Presence Locator
# =========================================================================
async def discover_patient(request):
    hospital_id = request.query_params.get("hospital_id", "node_a")
    q = request.query_params.get("q", "")
    if not q:
        return JSONResponse({"success": False, "error": "Search query is required."}, status_code=400)

    report = orchestrator.discover_patient(hospital_id, q)
    return JSONResponse({"success": True, "discovery": report})

# =========================================================================
# Granular Data Sharing & Verification Workflow
# =========================================================================
async def create_sharing_request(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    res = orchestrator.request_patient_data(
        from_hospital=data.get("from_hospital", "node_b"),
        to_hospital=data.get("to_hospital", "node_a"),
        patient_token=data.get("patient_token", ""),
        patient_name=data.get("patient_name", "Patient"),
        requested_categories=data.get("requested_categories", []),
        purpose=data.get("purpose", "CONTINUATION_OF_CARE"),
        justification=data.get("justification", "Clinical care continuity requirement."),
        requester_role="HOSPITAL_ADMIN"
    )
    return JSONResponse(res)

async def review_sharing_request(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    res = orchestrator.review_patient_data_request(
        request_id=data.get("request_id", ""),
        reviewer_hospital=data.get("reviewer_hospital", "node_a"),
        reviewer_name=data.get("reviewer_name", "Hospital Admin"),
        decision=data.get("decision", "APPROVED"),
        approved_categories=data.get("approved_categories", [])
    )
    return JSONResponse(res)

async def get_hospital_sharing_requests(request):
    hospital_id = request.query_params.get("hospital_id", "node_a")
    requests = FederationCoordinator.get_requests_for_hospital(hospital_id)
    return JSONResponse({"success": True, "requests": requests})

# =========================================================================
# Notifications Endpoints
# =========================================================================
async def get_notifications(request):
    hospital_id = request.query_params.get("hospital_id", "node_a")
    notifs = FederationCoordinator.get_notifications(hospital_id)
    unread_count = sum(1 for n in notifs if n["is_read"] == 0)
    return JSONResponse({"success": True, "notifications": notifs, "unread_count": unread_count})

async def mark_notifications_read(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    hospital_id = data.get("hospital_id", "node_a")
    FederationCoordinator.mark_notifications_read(hospital_id)
    return JSONResponse({"success": True})

# =========================================================================
# Existing Node Stats, Vault, Analytics & Audit Endpoints
# =========================================================================
async def get_nodes(request):
    nodes = orchestrator.get_nodes_info()
    return JSONResponse({"success": True, "nodes": nodes})

async def inspect_vault(request):
    node_id = request.path_params.get("node_id")
    limit = int(request.query_params.get("limit", 15))
    node = get_hospital_node(node_id)
    if not node:
        return JSONResponse({"success": False, "error": f"Unknown node: {node_id}"}, status_code=404)
    records = node.inspect_local_vault(limit)
    return JSONResponse({"success": True, "node_id": node_id, "limit": limit, "records": records})

async def execute_query(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    res = orchestrator.execute_collaborative_query(
        condition=data.get("condition"),
        severity=data.get("severity"),
        biomarker=data.get("biomarker"),
        abnormal_lab_only=bool(data.get("abnormal_lab_only", False)),
        biomarker_max=float(data["biomarker_max"]) if data.get("biomarker_max") is not None and data.get("biomarker_max") != "" else None,
        biomarker_min=float(data["biomarker_min"]) if data.get("biomarker_min") is not None and data.get("biomarker_min") != "" else None,
        medication=data.get("medication"),
        response_outcome=data.get("response_outcome"),
        min_adherence=float(data["min_adherence"]) if data.get("min_adherence") is not None and data.get("min_adherence") != "" else None,
        epsilon=float(data.get("epsilon", 1.0)),
        use_dp=bool(data.get("use_dp", True)),
        use_smpc=bool(data.get("use_smpc", True)),
        role=data.get("role", "CLINICAL_RESEARCHER"),
        purpose=data.get("purpose", "CLINICAL_RESEARCH"),
        researcher_name=data.get("researcher_name", "Dr. Clinical Investigator"),
        enforce_suppression=bool(data.get("enforce_suppression", True))
    )
    return JSONResponse(res)

async def get_budget(request):
    return JSONResponse({"success": True, "budget": orchestrator.dp_engine.get_budget_status()})

async def reset_budget(request):
    orchestrator.dp_engine.reset_budget()
    return JSONResponse({"success": True, "message": "Privacy budget reset to 10.0 ε", "budget": orchestrator.dp_engine.get_budget_status()})

async def get_audit(request):
    blocks = orchestrator.audit_ledger.get_blocks()
    return JSONResponse({"success": True, "total_blocks": len(blocks), "blocks": blocks})

async def verify_audit(request):
    status = orchestrator.audit_ledger.verify_integrity()
    return JSONResponse({"success": True, "status": status})

async def tamper_audit(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    block_index = int(data.get("block_index", 1))
    fake_name = data.get("fake_researcher", "UNAUTHORIZED_INTRUDER")
    result = orchestrator.audit_ledger.simulate_tampering(block_index, fake_name)
    return JSONResponse(result)

async def restore_audit(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    block_index = int(data.get("block_index", 1))
    original = data.get("original_researcher", "Dr. Clinical Investigator")
    orchestrator.audit_ledger.restore_block(block_index, original)
    return JSONResponse({"success": True, "message": f"Block #{block_index} restored."})

async def anonymize_data(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    condition = data.get("condition")
    k = int(data.get("k", 5))
    l = int(data.get("l", 2))
    role = data.get("role", "CLINICAL_RESEARCHER")
    purpose = data.get("purpose", "CLINICAL_RESEARCH")
    res = orchestrator.export_anonymized_microdata(condition=condition, role=role, purpose=purpose, k=k, l=l)
    return JSONResponse(res)

async def serve_index(request):
    index_file = FRONTEND_DIR / "index.html"
    return FileResponse(index_file)

routes = [
    Route("/", serve_index),
    # Hospital Auth & Sessions
    Route("/api/auth/login", auth_login, methods=["POST"]),
    # Patient Records & Discovery
    Route("/api/patient/search", search_local_patients, methods=["GET"]),
    Route("/api/patient/profile", get_patient_profile, methods=["GET"]),
    Route("/api/patient/discover", discover_patient, methods=["GET"]),
    Route("/api/patient/add", add_new_patient, methods=["POST"]),
    Route("/api/patient/encounter/add", add_clinical_encounter, methods=["POST"]),
    # Inter-Hospital Sharing Requests & Review
    Route("/api/sharing/request", create_sharing_request, methods=["POST"]),
    Route("/api/sharing/review", review_sharing_request, methods=["POST"]),
    Route("/api/sharing/requests", get_hospital_sharing_requests, methods=["GET"]),
    # Top-bar Notifications
    Route("/api/notifications", get_notifications, methods=["GET"]),
    Route("/api/notifications/mark-read", mark_notifications_read, methods=["POST"]),
    # Federation stats, vault, analytics & audit
    Route("/api/nodes", get_nodes, methods=["GET"]),
    Route("/api/vault/{node_id}", inspect_vault, methods=["GET"]),
    Route("/api/query", execute_query, methods=["POST"]),
    Route("/api/budget", get_budget, methods=["GET"]),
    Route("/api/budget/reset", reset_budget, methods=["POST"]),
    Route("/api/audit", get_audit, methods=["GET"]),
    Route("/api/audit/verify", verify_audit, methods=["POST"]),
    Route("/api/audit/tamper", tamper_audit, methods=["POST"]),
    Route("/api/audit/restore", restore_audit, methods=["POST"]),
    Route("/api/anonymize", anonymize_data, methods=["POST"]),
    Mount("/", app=StaticFiles(directory=str(FRONTEND_DIR)), name="static")
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=False)
