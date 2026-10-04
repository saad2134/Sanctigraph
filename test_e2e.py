import asyncio
import sys
import time
import httpx

from services.orchestrator.graph.engine import engine
from services.orchestrator.models.schemas import AlertPayload


async def test_full_pipeline():
    print("====================================================")
    print("SANCTIGRAPH END-TO-END DEMO TEST WITH LIVE TARGET")
    print("====================================================")

    # 1. Inject fault into live Payment Service
    print("\n1. Injecting Connection Starvation Fault into :8001...")
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://127.0.0.1:8001/fault/connection_starvation")
        assert resp.status_code == 200, f"Failed to inject fault: {resp.text}"
        print(f"   [OK] Fault Injected: {resp.json()['symptoms']}")

    # Wait for metric to reflect fault
    await asyncio.sleep(1.0)

    # 2. Ingest Alert
    alert = AlertPayload(
        alertname="High504ErrorRate",
        severity="P0",
        service="payment-checkout-api",
        summary="High 504 Gateway Timeouts: PostgreSQL pool saturated",
        description="Payment API dropping >25% of transactions. Active connections at 20/20 capacity.",
    )

    print("\n2. Ingesting Alert into Sanctigraph Orchestrator...")
    record = await engine.ingest_alert(alert)
    print(f"   [OK] Incident Created: {record.incident_id} | Status: {record.status}")

    # 3. Wait for Triage Pipeline to reach Approval Gate
    print("\n3. Waiting for Triage Pipeline to reach Approval Gate...")
    for _ in range(20):
        await asyncio.sleep(0.5)
        rec = engine.incidents[record.incident_id]
        if rec.status == "AWAITING_APPROVAL":
            break

    rec = engine.incidents[record.incident_id]
    assert rec.status == "AWAITING_APPROVAL", f"Expected AWAITING_APPROVAL, got {rec.status}"
    print(f"   [OK] Status: {rec.status}")
    print(f"   [OK] Root Cause: {rec.rca.summary}")
    print(f"   [OK] Blast Radius: {rec.blast_radius.risk_tier} (Score: {rec.blast_radius.risk_score}/100)")
    print(f"   [OK] Plan Steps: {len(rec.plan.steps)} steps | Hash: {rec.plan.plan_hash[:16]}...")
    print(f"   [OK] HMAC Token: {rec.approval_token.signature[:16]}... (Expires in 300s)")

    # 4. Security Check: Reject forged token
    print("\n4. Testing Approval Gate Security...")
    try:
        await engine.approve_and_execute(rec.incident_id, "forged_signature_123")
        assert False, "Should have rejected forged token!"
    except ValueError as e:
        print(f"   [PASS] Forged token rejected as expected: {e}")

    # 5. Submit valid HMAC cryptographic signature
    print("\n5. Submitting Valid HMAC Cryptographic Signature...")
    valid_sig = rec.approval_token.signature
    res = await engine.approve_and_execute(rec.incident_id, valid_sig)
    print(f"   [OK] Execution Result: {res}")
    assert res["success"] is True, f"Execution failed: {res}"

    # 6. Wait for Execution & Adaptive Canary Verification
    print("\n6. Waiting for Adaptive 2-Phase Canary Verification...")
    for i in range(35):
        await asyncio.sleep(1.0)
        rec = engine.incidents[record.incident_id]
        if rec.status in ["RESOLVED", "ROLLBACK", "FAILED"]:
            break
        if i % 3 == 0:
            print(f"      Canary watching... current status: {rec.status}")

    print(f"\n   [OK] Final Incident Status: {rec.status}")
    assert rec.status == "RESOLVED", f"Expected RESOLVED, got {rec.status}"

    if rec.canary:
        print(f"   [OK] Canary Phase: {rec.canary.phase}")
        print(f"   [OK] Canary SLO Restored: {rec.canary.slo_restored}")
        print(f"   [OK] Median Error Rate: {rec.canary.median_error_rate}%")
        print(f"   [OK] Median P99 Latency: {rec.canary.median_p99_latency}ms")

    # 7. Check post-mortem
    assert rec.postmortem is not None, "Post-mortem should be generated!"
    print("\n7. Post-Mortem Generated Successfully!")
    print(f"   [OK] Length: {len(rec.postmortem)} characters")
    print("----------------------------------------------------")
    print(rec.postmortem[:350] + "...\n----------------------------------------------------")

    print("\n>>> ALL VERIFICATION TESTS PASSED WITH 100% SUCCESS! <<<")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
