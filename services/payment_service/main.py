import asyncio
import json
import logging
import random
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("payment_service")

app = FastAPI(
    title="Checkout & Payment Microservice Target",
    description="High-throughput payment processing service with realistic telemetry and fault injection endpoints for Sanctigraph",
    version="1.4.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ServiceState:
    def __init__(self):
        self.service_name = "payment-checkout-api"
        self.version = "v1.4.2"
        self.active_db_connections = 12
        self.max_connections = 20
        self.worker_replicas = 2
        self.memory_mb = 145.0
        self.fault_connection_starvation = False
        self.fault_oom_loop = False
        self.total_requests = 1420
        self.error_requests = 4
        self.recent_request_outcomes: List[bool] = [True] * 30
        self.recent_latencies: List[float] = [42.1, 38.5, 45.0, 41.2, 39.8, 44.1]
        self.recent_logs: List[Dict] = []
        self.max_logs = 200

    def add_log(self, level: str, message: str, context: Optional[Dict] = None):
        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level,
            "service": self.service_name,
            "message": message,
            "context": context or {},
        }
        self.recent_logs.append(entry)
        if len(self.recent_logs) > self.max_logs:
            self.recent_logs.pop(0)

    def get_metrics_snapshot(self) -> Dict:
        req_total = self.total_requests
        err_total = self.error_requests
        # Rolling error rate over recent window (mirrors Prometheus rate([1m]))
        if self.recent_request_outcomes:
            errors_in_window = self.recent_request_outcomes.count(False)
            rate = (errors_in_window / len(self.recent_request_outcomes)) * 100.0
        else:
            rate = 0.0

        sorted_lat = sorted(self.recent_latencies) if self.recent_latencies else [40.0]
        p99_idx = int(len(sorted_lat) * 0.99)
        p99_val = sorted_lat[min(p99_idx, len(sorted_lat) - 1)]

        return {
            "service": self.service_name,
            "version": self.version,
            "total_requests": req_total,
            "error_requests": err_total,
            "error_rate_percent": round(rate, 2),
            "p99_latency_ms": round(p99_val, 1),
            "active_db_connections": self.active_db_connections,
            "max_db_connections": self.max_connections,
            "worker_replicas": self.worker_replicas,
            "memory_usage_mb": round(self.memory_mb, 1),
            "fault_active": self.fault_connection_starvation or self.fault_oom_loop,
            "status": "CRITICAL" if (self.fault_connection_starvation or self.fault_oom_loop) else "HEALTHY",
        }


state = ServiceState()


class ChargeRequest(BaseModel):
    amount_cents: int = Field(default=4999, ge=100)
    currency: str = Field(default="USD")
    customer_id: str = Field(default="cust_8921a")
    idempotency_key: Optional[str] = None


class ReconfigureRequest(BaseModel):
    max_connections: Optional[int] = Field(default=None, ge=10, le=200)
    worker_replicas: Optional[int] = Field(default=None, ge=1, le=20)
    reset_pool: bool = Field(default=False)
    clear_faults: bool = Field(default=True)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Payment Microservice synthetic background traffic worker...")
    asyncio.create_task(background_traffic_generator())


async def background_traffic_generator():
    """Generates realistic synthetic background payment requests and logs."""
    while True:
        try:
            await asyncio.sleep(0.3)
            state.total_requests += 1

            if state.fault_connection_starvation:
                state.active_db_connections = state.max_connections
                latency = random.uniform(520.0, 950.0)
                state.error_requests += 1
                state.recent_request_outcomes.append(False)
                if len(state.recent_request_outcomes) > 30:
                    state.recent_request_outcomes.pop(0)
                state.recent_latencies.append(latency)
                if len(state.recent_latencies) > 50:
                    state.recent_latencies.pop(0)

                if random.random() < 0.4:
                    state.add_log(
                        "ERROR",
                        f"Database pool timeout: could not acquire connection from pool [active={state.active_db_connections}/{state.max_connections}, wait_time={int(latency)}ms]. Endpoint: /api/v1/charge",
                        {"error": "PoolExhaustionTimeout", "code": 504, "db_host": "primary-postgres.prod.internal:5432"},
                    )
            elif state.fault_oom_loop:
                state.memory_mb = min(1900.0, state.memory_mb + random.uniform(50.0, 120.0))
                latency = random.uniform(200.0, 450.0)
                state.error_requests += 1
                state.recent_request_outcomes.append(False)
                if len(state.recent_request_outcomes) > 30:
                    state.recent_request_outcomes.pop(0)
                state.recent_latencies.append(latency)
                if len(state.recent_latencies) > 50:
                    state.recent_latencies.pop(0)

                if random.random() < 0.4:
                    state.add_log(
                        "FATAL",
                        f"Runtime OOM: process RSS memory ({int(state.memory_mb)}MB) exceeded cgroup limit (512MB). Pod restart imminent.",
                        {"exit_code": 137, "signal": "SIGKILL", "component": "v8_heap"},
                    )
            else:
                # Normal healthy operation
                state.active_db_connections = max(4, min(state.max_connections - 4, int(state.active_db_connections + random.choice([-1, 0, 1]))))
                state.memory_mb = max(120.0, min(160.0, state.memory_mb + random.choice([-1.5, 0.0, 1.5])))
                latency = random.uniform(32.0, 58.0)
                state.recent_request_outcomes.append(True)
                if len(state.recent_request_outcomes) > 30:
                    state.recent_request_outcomes.pop(0)
                state.recent_latencies.append(latency)
                if len(state.recent_latencies) > 50:
                    state.recent_latencies.pop(0)

                if random.random() < 0.08:
                    state.add_log(
                        "INFO",
                        f"Processed payment charge successfully: ${random.randint(15, 120)}.00 via Stripe gateway. Latency: {int(latency)}ms",
                        {"status": "SUCCESS", "gateway": "stripe_v3"},
                    )
        except Exception as e:
            logger.error(f"Traffic generator error: {e}")


@app.get("/healthz")
def health_check():
    snapshot = state.get_metrics_snapshot()
    if snapshot["status"] == "CRITICAL":
        payload = json.dumps({
            "status": "DEGRADED",
            "detail": "High error rate detected in upstream connection pool",
            "snapshot": snapshot,
        })
        return Response(content=payload, media_type="application/json", status_code=503)
    return {"status": "HEALTHY", "snapshot": snapshot}


@app.get("/telemetry")
def telemetry_endpoint():
    return {"status": "OK", "snapshot": state.get_metrics_snapshot()}


@app.get("/metrics")
def prometheus_metrics():
    snapshot = state.get_metrics_snapshot()
    lines = [
        "# HELP payment_requests_total Total number of payment charge requests",
        "# TYPE payment_requests_total counter",
        f"payment_requests_total {snapshot['total_requests']}",
        "# HELP payment_errors_total Total number of failed payment requests",
        "# TYPE payment_errors_total counter",
        f"payment_errors_total {snapshot['error_requests']}",
        "# HELP payment_error_rate Current error rate percentage",
        "# TYPE payment_error_rate gauge",
        f"payment_error_rate {snapshot['error_rate_percent']}",
        "# HELP payment_p99_latency_ms 99th percentile request latency in ms",
        "# TYPE payment_p99_latency_ms gauge",
        f"payment_p99_latency_ms {snapshot['p99_latency_ms']}",
        "# HELP payment_active_db_connections Number of in-use PostgreSQL connections",
        "# TYPE payment_active_db_connections gauge",
        f"payment_active_db_connections {snapshot['active_db_connections']}",
        "# HELP payment_max_db_connections Configured pool capacity limit",
        "# TYPE payment_max_db_connections gauge",
        f"payment_max_db_connections {snapshot['max_db_connections']}",
        "# HELP payment_worker_replicas Number of Kubernetes container replicas",
        "# TYPE payment_worker_replicas gauge",
        f"payment_worker_replicas {snapshot['worker_replicas']}",
        "# HELP payment_memory_usage_mb Container memory RSS in megabytes",
        "# TYPE payment_memory_usage_mb gauge",
        f"payment_memory_usage_mb {snapshot['memory_usage_mb']}",
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain")


@app.get("/logs")
def get_logs(limit: int = 50, level: Optional[str] = None):
    logs = state.recent_logs
    if level:
        logs = [l for l in logs if l["level"].upper() == level.upper()]
    return {"service": state.service_name, "count": len(logs), "logs": logs[-limit:]}


@app.post("/api/v1/charge")
def process_charge(req: ChargeRequest):
    state.total_requests += 1

    if state.fault_connection_starvation:
        state.error_requests += 1
        state.add_log(
            "ERROR",
            f"HTTP 504: Database pool timeout for customer {req.customer_id} on amount {req.amount_cents}",
            {"customer_id": req.customer_id, "amount": req.amount_cents},
        )
        raise HTTPException(
            status_code=504,
            detail=f"Gateway Timeout: Connection pool exhausted (active={state.active_db_connections}/{state.max_connections}). Could not acquire DB lease within 500ms.",
        )

    if state.fault_oom_loop:
        state.error_requests += 1
        state.add_log(
            "ERROR",
            f"HTTP 500: Internal Server Error - V8 heap memory pressure while serializing ledger entry for {req.customer_id}",
            {"customer_id": req.customer_id},
        )
        raise HTTPException(status_code=500, detail="Internal Server Error: Memory threshold breached")

    return {
        "status": "APPROVED",
        "charge_id": f"ch_{random.randint(100000, 999999)}",
        "amount_cents": req.amount_cents,
        "currency": req.currency,
        "customer_id": req.customer_id,
        "timestamp": time.time(),
    }


# ==========================================
# FAULT INJECTION CONTROLLERS (FOR DEMO DAY)
# ==========================================


@app.post("/fault/connection_starvation")
def inject_connection_starvation():
    """Injects simulated connection pool exhaustion leading to 504 Gateway Timeouts."""
    state.fault_connection_starvation = True
    state.fault_oom_loop = False
    state.active_db_connections = state.max_connections
    # Immediately seed sliding window with failing requests (28.5% error rate, high P99)
    state.recent_request_outcomes = [False] * 10 + [True] * 20
    state.recent_latencies = [840.5, 910.2, 780.0, 950.1, 885.3]

    state.add_log(
        "CRITICAL",
        "ALERT FIRED: High504ErrorRate - payment-checkout-api is dropping >25% of charge transactions. Postgres pool saturated.",
        {"alert_name": "High504ErrorRate", "severity": "P0", "sli_error_rate": 0.28},
    )
    logger.warning("FAULT INJECTED: Connection pool starvation active!")
    return {
        "status": "FAULT_INJECTED",
        "fault": "connection_pool_starvation",
        "symptoms": ["504 Gateway Timeouts", "Active DB connections saturated at max", "High P99 latency"],
        "metrics": state.get_metrics_snapshot(),
    }


@app.post("/fault/oom_loop")
def inject_oom_loop():
    """Injects simulated memory leak / CrashLoopBackOff."""
    state.fault_oom_loop = True
    state.fault_connection_starvation = False
    state.memory_mb = 1250.0
    # Immediately seed sliding window with 500 errors (40% error rate, elevated latency)
    state.recent_request_outcomes = [False] * 12 + [True] * 18
    state.recent_latencies = [420.0, 580.0, 650.0, 710.0]

    state.add_log(
        "CRITICAL",
        "ALERT FIRED: PodCrashLooping - Container payment-checkout-api terminated with exit code 137 (OOMKilled)",
        {"alert_name": "PodCrashLooping", "severity": "P0", "cgroup_limit_mb": 512, "actual_rss_mb": 1250},
    )
    logger.warning("FAULT INJECTED: OOM Loop active!")
    return {
        "status": "FAULT_INJECTED",
        "fault": "oom_crash_loop",
        "symptoms": ["Pod exit code 137", "500 Internal Server Errors", "Memory limit exceeded"],
        "metrics": state.get_metrics_snapshot(),
    }


@app.post("/fault/clear")
def clear_faults():
    """Clears all injected faults, restoring healthy baseline."""
    state.fault_connection_starvation = False
    state.fault_oom_loop = False
    state.active_db_connections = 12
    state.memory_mb = 145.0
    state.recent_request_outcomes = [True] * 30
    state.recent_latencies = [42.1, 38.5, 45.0, 41.2, 39.8, 44.1]
    state.add_log("INFO", "All fault injections cleared. Reverting to healthy state.", {})
    logger.info("Faults cleared.")
    return {"status": "HEALTHY", "metrics": state.get_metrics_snapshot()}


@app.post("/admin/reconfigure")
def reconfigure_service(req: ReconfigureRequest):
    """
    Administrative endpoint called by Sanctigraph Remediation Agent (LocalSandboxAdapter)
    to scale workers, expand connection pool, or reset connection leases.
    """
    actions_taken = []
    if req.max_connections is not None:
        state.max_connections = req.max_connections
        actions_taken.append(f"Expanded max_connections to {req.max_connections}")

    if req.worker_replicas is not None:
        state.worker_replicas = req.worker_replicas
        actions_taken.append(f"Scaled worker replicas to {req.worker_replicas}")

    if req.reset_pool:
        state.active_db_connections = 8
        actions_taken.append("Reset active DB connection pool leases")

    if req.clear_faults:
        state.fault_connection_starvation = False
        state.fault_oom_loop = False
        state.recent_request_outcomes = [True] * 30
        state.recent_latencies = [42.1, 38.5, 45.0, 41.2, 39.8, 44.1]
        actions_taken.append("Cleared active fault conditions")

    state.add_log(
        "NOTICE",
        f"Administrative remediation executed by Sanctigraph: {', '.join(actions_taken)}",
        {"caller": "Sanctigraph-Agent", "actions": actions_taken},
    )

    logger.info(f"Admin remediation executed: {actions_taken}")
    return {
        "status": "RECONFIGURED",
        "actions_taken": actions_taken,
        "new_metrics": state.get_metrics_snapshot(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
