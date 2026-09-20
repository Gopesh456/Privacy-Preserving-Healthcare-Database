"""
Backend API Server for Privacy-Preserving Healthcare Database.
Uses Starlette + Uvicorn to serve REST APIs and the interactive frontend.
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

orchestrator = FederatedOrchestrator(total_epsilon_budget=10.0)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

async def get_nodes(request):
    nodes = orchestrator.get_nodes_info()
    return JSONResponse({"success": True, "nodes": nodes})

async def inspect_vault(request):
    node_id = request.path_params.get("node_id")
    limit = int(request.query_params.get("limit", 15))
    if node_id == "node_a":
        records = orchestrator.node_a.inspect_local_vault(limit)
    elif node_id == "node_b":
        records = orchestrator.node_b.inspect_local_vault(limit)
    elif node_id == "node_c":
        records = orchestrator.node_c.inspect_local_vault(limit)
    else:
        return JSONResponse({"success": False, "error": f"Unknown node: {node_id}"}, status_code=404)
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
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=True)
