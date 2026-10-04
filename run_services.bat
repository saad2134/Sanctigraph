@echo off
echo ============================================================
echo   SANCTIGRAPH: Autonomous SRE Incident Triage & Remediation
echo ============================================================
echo.
echo Starting Payment Microservice Target on http://127.0.0.1:8001...
start "Sanctigraph - Payment Service (:8001)" python -m uvicorn services.payment_service.main:app --port 8001 --host 127.0.0.1
timeout /t 2 /nobreak >nul

echo Starting Sanctigraph Orchestrator & Command Center on http://127.0.0.1:8000...
start "Sanctigraph - Orchestrator (:8000)" python -m uvicorn services.orchestrator.api.main:app --port 8000 --host 127.0.0.1
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo   Services are online!
echo   - Command Center UI:  http://127.0.0.1:8000/
echo   - Target API & Docs:  http://127.0.0.1:8001/docs
echo   - Orchestrator Docs:  http://127.0.0.1:8000/docs
echo ============================================================
echo.
pause
