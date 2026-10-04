import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import httpx
from pydantic import BaseModel

from ..graph.engine import engine
from ..models.schemas import AlertPayload, IncidentRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sanctigraph.api")

app = FastAPI(
    title="Sanctigraph Autonomous SRE Orchestrator API",
    description="Deterministic, cryptographically gated incident response & remediation agent",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApproveRequest(BaseModel):
    signature: str


class RejectRequest(BaseModel):
    reason: Optional[str] = "Operator rejected remediation plan"


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_INDEX = STATIC_DIR / "index.html"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/favicon.ico")
def get_favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    return Response(status_code=404)


@app.get("/")
@app.get("/dashboard")
def get_dashboard():
    if STATIC_INDEX.exists():
        return FileResponse(STATIC_INDEX)
    return {"message": "Sanctigraph Orchestrator API online. Dashboard file not found."}


@app.get("/api/health")
def health():
    return {"status": "ONLINE", "version": "2.0.0", "target_service": engine.target_url}


@app.get("/api/incidents")
def list_incidents() -> List[Dict]:
    return [rec.model_dump() for rec in engine.incidents.values()]


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str) -> Dict:
    if incident_id not in engine.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return engine.incidents[incident_id].model_dump()


@app.post("/api/incidents/webhook")
async def incident_webhook(alert: AlertPayload):
    record = await engine.ingest_alert(alert)
    return {"status": "INGESTED", "incident_id": record.incident_id, "record": record.model_dump()}


@app.post("/api/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str, req: ApproveRequest):
    try:
        res = await engine.approve_and_execute(incident_id, req.signature)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/incidents/{incident_id}/reject")
async def reject_incident(incident_id: str, req: Optional[RejectRequest] = None):
    try:
        reason = req.reason if req and req.reason else "Operator rejected remediation plan"
        res = await engine.reject_and_escalate(incident_id, reason)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/incidents/{incident_id}/postmortem")
def get_postmortem(incident_id: str):
    if incident_id not in engine.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    record = engine.incidents[incident_id]
    if not record.postmortem:
        raise HTTPException(status_code=400, detail="Post-mortem not yet generated (incident still active)")
    return Response(content=record.postmortem, media_type="text/markdown")


@app.get("/api/incidents/{incident_id}/stream")
async def stream_incident_events(incident_id: str, request: Request):
    """Server-Sent Events (SSE) endpoint providing real-time UI state updates."""
    if incident_id not in engine.incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    q = engine.subscribe(incident_id)

    async def event_generator():
        # First send initial snapshot
        initial_data = json.dumps({"event": "SNAPSHOT", "data": engine.incidents[incident_id].model_dump()})
        yield f"data: {initial_data}\n\n"

        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(q.get(), timeout=15.0)
                payload = json.dumps(msg)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                # Keep-alive heartbeat
                yield f": heartbeat\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ==========================================
# 1-CLICK HACKATHON DEMO CONTROLLER
# ==========================================


@app.post("/api/demo/trigger")
async def trigger_demo_incident(fault: str = "connection_starvation"):
    """
    1-Click Hackathon Demo Trigger:
    1. Injects fault into Payment Microservice Target (:8001).
    2. Emits Prometheus P0 Alertmanager webhook.
    3. Triggers Sanctigraph autonomous triage pipeline.
    """
    async with engine.get_http_client() as client:
        try:
            if fault == "oom_loop":
                await client.post(f"{engine.target_url}/fault/oom_loop", timeout=3.0)
                alert = AlertPayload(
                    alertname="PodCrashLooping",
                    severity="P0",
                    service="payment-checkout-api",
                    summary="OOMKilled exit code 137 on payment-checkout-api",
                    description="Container RSS memory exceeded 512MB cgroup limit. Service dropping requests with 500s.",
                )
            else:
                await client.post(f"{engine.target_url}/fault/connection_starvation", timeout=3.0)
                alert = AlertPayload(
                    alertname="High504ErrorRate",
                    severity="P0",
                    service="payment-checkout-api",
                    summary="High 504 Gateway Timeouts: PostgreSQL pool saturated",
                    description="Payment API dropping >25% of charge transactions. Active connections at 20/20 capacity.",
                )
        except Exception as e:
            logger.error(f"Error calling target service: {e}")
            alert = AlertPayload(
                alertname="High504ErrorRate",
                severity="P0",
                service="payment-checkout-api",
                summary="PostgreSQL connection pool exhausted",
                description="Transaction error rate breached 25% threshold.",
            )

    record = await engine.ingest_alert(alert)
    return {
        "status": "DEMO_INCIDENT_TRIGGERED",
        "fault_injected": fault,
        "incident_id": record.incident_id,
        "initial_record": record.model_dump(),
    }


@app.get("/api/telemetry")
async def get_target_telemetry():
    """Proxy endpoint to fetch telemetry from the target microservice safely with fallback."""
    try:
        async with engine.get_http_client() as client:
            resp = await client.get(f"{engine.target_url}/healthz", timeout=2.0)
            data = resp.json()
            if "snapshot" in data:
                return {"status": data.get("status", "HEALTHY"), "snapshot": data["snapshot"]}
    except Exception as e:
        logger.warning(f"Could not reach target service for telemetry: {e}")
    return {
        "status": "HEALTHY",
        "snapshot": {
            "service": "payment-checkout-api",
            "error_rate_percent": 0.0,
            "p99_latency_ms": 42.0,
            "active_db_connections": 12,
            "max_db_connections": 20,
            "worker_replicas": 2,
            "fault_active": False,
        },
    }


@app.post("/api/demo/clear")
async def clear_target_faults():
    """Proxy endpoint to clear faults on target microservice."""
    engine.incidents.clear()
    engine.alert_sliding_window.clear()
    try:
        async with engine.get_http_client() as client:
            resp = await client.post(f"{engine.target_url}/fault/clear", timeout=2.0)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Could not reach target service to clear faults: {e}")
    return {"status": "CLEARED"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

