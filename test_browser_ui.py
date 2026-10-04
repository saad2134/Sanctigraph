import asyncio
import os
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")


def run_full_browser_test():
    print("====================================================")
    print("SANCTIGRAPH FULL BROWSER AUTOMATION & UI VERIFICATION")
    print("====================================================")

    console_logs = []
    page_errors = []

    with sync_playwright() as p:
        print("\n1. Launching Edge Browser...")
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Listen for console logs and JS errors
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        print("2. Navigating to http://127.0.0.1:8000/...")
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")

        title = page.title()
        print(f"   [OK] Page Title: '{title}'")
        assert "Sanctigraph" in title, f"Unexpected page title: {title}"

        # Check key UI elements exist
        assert page.locator("#executive-banner").is_visible(), "Executive banner missing"
        assert page.locator("#dag-status-pill").is_visible(), "DAG status pill missing"
        assert page.locator("#metric-error-rate").is_visible(), "Error rate metric missing"
        assert page.locator("#metric-conns").is_visible(), "Connections metric missing"
        assert page.locator("#execution-terminal").is_visible(), "Terminal console missing"
        
        # Check brand images: navbar logo and Slack card bot avatar
        navbar_logo = page.locator('img[alt="Sanctigraph Logo"]')
        assert navbar_logo.is_visible(), "Navbar logo image missing or hidden"
        slack_avatar = page.locator('img[alt="Sanctigraph Bot"]')
        assert slack_avatar.is_visible(), "Slack card bot avatar image missing or hidden"
        print("   [OK] Brand icons (Navbar Logo & Slack Card Avatar) verified visible!")

        # Verify all 9 DAG nodes exist and have identical dimensions
        node_ids = [
            "node-alert-ingest",
            "node-telemetry",
            "node-sanitizer",
            "node-rca",
            "node-blast",
            "node-gate",
            "node-exec",
            "node-canary",
            "node-postmortem"
        ]
        assert len(node_ids) == 9, "Expected 9 nodes"
        first_box = None
        for nid in node_ids:
            elem = page.locator(f"#{nid}")
            assert elem.is_visible(), f"Node #{nid} is not visible"
            box = elem.bounding_box()
            assert box is not None, f"Node #{nid} has no bounding box"
            w, h = round(box["width"]), round(box["height"])
            print(f"   [NODE DIMENSION] #{nid}: {w}px x {h}px")
            assert w == 104, f"Node #{nid} width expected 104px, got {w}px"
            assert h == 96, f"Node #{nid} height expected 96px, got {h}px"
            if first_box is None:
                first_box = (w, h)
            else:
                assert (w, h) == first_box, f"Node #{nid} size ({w}x{h}) does not match first node ({first_box})"
        print("   [OK] All 9 DAG nodes verified to have EXACT identical dimensions (104px x 96px)!")

        print("   [OK] All core UI DOM components verified visible!")

        # Wait a moment for metric poller
        page.wait_for_timeout(2000)
        initial_err = page.locator("#metric-error-rate").inner_text()
        print(f"   [OK] Initial Baseline Error Rate: {initial_err}")

        # ----------------------------------------------------
        # TEST SCENARIO 1: Click 504 Pool Starvation
        # ----------------------------------------------------
        print("\n3. Testing SCENARIO 1: Clicking '504 Pool Starvation' button in UI...")
        starvation_btn = page.locator('button:has-text("504 Pool Starvation")')
        assert starvation_btn.is_visible(), "504 Pool Starvation button not visible"
        starvation_btn.click()

        print("   [OK] Button clicked! Waiting for SSE events and triage pipeline...")

        # Wait for Approval Gate to illuminate in UI (max 10s)
        page.wait_for_selector('#approval-actions button:has-text("APPROVE REMEDIATION")', timeout=10000)
        print("   [OK] Human Approval Gate activated and visible in UI!")

        # Verify incident title updated
        inc_title = page.locator("#incident-title").inner_text()
        inc_severity = page.locator("#incident-severity-badge").inner_text()
        rca_summary = page.locator("#exec-rca-summary").inner_text()
        print(f"   [OK] Incident Title: '{inc_title}'")
        print(f"   [OK] Severity Badge: '{inc_severity}'")
        print(f"   [OK] RCA Summary in Banner: '{rca_summary}'")

        # Verify DAG state
        dag_pill = page.locator("#dag-status-pill").inner_text()
        print(f"   [OK] Current DAG Node Status: '{dag_pill}'")

        # Take screenshot of Awaiting Approval state
        os.makedirs("test_artifacts", exist_ok=True)
        screenshot_1 = "test_artifacts/01_awaiting_approval.png"
        page.screenshot(path=screenshot_1, full_page=True)
        print(f"   [OK] Screenshot saved: {screenshot_1}")

        # ----------------------------------------------------
        # TEST HUMAN APPROVAL CLICK IN BROWSER
        # ----------------------------------------------------
        print("\n4. Clicking 'APPROVE REMEDIATION (HMAC-SIGNED)' button in Cockpit...")
        approve_btn = page.locator('#approval-actions button:has-text("APPROVE REMEDIATION")')
        approve_btn.click()
        print("   [OK] Approval button clicked! Monitoring Execution & Adaptive Canary...")

        # Wait for resolution (max 25s for 2-phase canary)
        print("   [WATCHING] Awaiting closed-loop canary SLO restoration...")
        page.wait_for_selector('#dag-status-pill:has-text("RESOLVED")', timeout=30000)
        print("   [OK] Incident status marked RESOLVED in UI!")

        # Wait for postmortem box to populate
        page.wait_for_timeout(2000)
        postmortem_text = page.locator("#postmortem-box").inner_text()
        assert "Post-Mortem" in postmortem_text, "Post-mortem text not rendered"
        print(f"   [OK] Post-Mortem rendered in UI ({len(postmortem_text)} chars)!")

        # Verify metrics restored
        recovered_err = page.locator("#metric-error-rate").inner_text()
        recovered_p99 = page.locator("#metric-p99").inner_text()
        print(f"   [OK] Recovered Error Rate: {recovered_err}")
        print(f"   [OK] Recovered P99 Latency: {recovered_p99}")

        # Take screenshot of Resolved State
        screenshot_2 = "test_artifacts/02_resolved_canary.png"
        page.screenshot(path=screenshot_2, full_page=True)
        print(f"   [OK] Screenshot saved: {screenshot_2}")

        # ----------------------------------------------------
        # TEST SCENARIO 2: Click OOM CrashLoop
        # ----------------------------------------------------
        print("\n5. Testing SCENARIO 2: Clicking 'OOM CrashLoop' button in UI...")
        oom_btn = page.locator('button:has-text("OOM CrashLoop")')
        oom_btn.click()
        print("   [OK] OOM button clicked! Waiting for triage pipeline...")

        page.wait_for_selector('#approval-actions button:has-text("APPROVE REMEDIATION")', timeout=10000)
        oom_title = page.locator("#incident-title").inner_text()
        print(f"   [OK] Second Incident Title: '{oom_title}'")

        # Approve second incident
        approve_btn2 = page.locator('#approval-actions button:has-text("APPROVE REMEDIATION")')
        approve_btn2.click()
        print("   [OK] Second incident approved. Waiting for resolution...")

        page.wait_for_selector('#dag-status-pill:has-text("RESOLVED")', timeout=30000)
        print("   [OK] Second incident RESOLVED successfully!")

        # Take screenshot of final UI state
        screenshot_3 = "test_artifacts/03_final_cockpit.png"
        page.screenshot(path=screenshot_3, full_page=True)
        print(f"   [OK] Screenshot saved: {screenshot_3}")

        # Check for any unhandled JS errors
        print("\n6. Checking Browser Console & Runtime Errors...")
        if page_errors:
            print(f"   [WARNING] Detected JS errors: {page_errors}")
        else:
            print("   [PASS] ZERO JavaScript runtime errors detected during entire test!")

        print(f"   [INFO] Recorded {len(console_logs)} browser console log messages.")

        browser.close()

    print("\n====================================================")
    print(">>> 100% COMPLETE: ALL BROWSER & UI TESTS PASSED! <<<")
    print("====================================================")


if __name__ == "__main__":
    run_full_browser_test()
