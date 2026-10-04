import os
import subprocess
import time
import httpx
from playwright.sync_api import sync_playwright

def build_hd_demo():
    build_dir = "video_build"
    raw_dir = os.path.join(build_dir, "raw_video")
    os.makedirs(raw_dir, exist_ok=True)

    segments = [
        ("seg01_intro.mp3", "Welcome to Sanctigraph: an autonomous, cryptographically guarded Site Reliability Engineering agent built for WCC Launchpad 30 Track 01, Agentic AI."),
        ("seg02_problem.mp3", "When production outages strike, SRE teams scramble across chaotic channels, deciphering alerts and running risky, unvalidated shell scripts. The average incident triage scramble takes 49 minutes, costing thousands of dollars per minute."),
        ("seg03_trigger.mp3", "Watch what happens when we inject a severe P0 incident: PostgreSQL connection pool starvation on our payment microservice."),
        ("seg04_telemetry.mp3", "Instantly, error rates surge past 25% and P99 latency spikes above 800 milliseconds. Sanctigraph immediately engages. Node 1 clusters the alert storm within a 3-minute tumbling topology window. Node 2 ingests telemetry, logs, and Git deployments in parallel."),
        ("seg05_sanitizer.mp3", "Before passing data to LLMs, Node 3 runs our deterministic sanitizer: stripping JWTs, credentials, and emails, while wrapping untrusted application logs inside XML boundary tags to neutralize indirect prompt injection attacks."),
        ("seg06_rca_blast.mp3", "Node 4 synthesizes the root cause in under two seconds, correctly pinpointing Git PR 104, which reduced connection timeouts. Node 5 evaluates the blast radius, classifying the remediation as Tier 2 Guarded-Write requiring human signoff."),
        ("seg07_hmac_gate.mp3", "Node 6 generates a typed DAG remediation plan, and Node 7 locks the pipeline behind an immutable HMAC-SHA256 approval token. If the plan or parameters mutate, the token instantly invalidates. Responders can review from the cockpit or via interactive Slack cards."),
        ("seg08_execution.mp3", "We click Approve. The single-use nonce is burned. Node 8 executes our zero-raw-shell tool contracts: resetting connection leases, expanding pool capacity to 50, and scaling pod replicas to 4."),
        ("seg09_canary.mp3", "Instead of fixed-timer rollbacks that flap prematurely, Node 9 launches our Adaptive 2-Phase Canary. Phase 1 synchronizes pod readiness probes. Phase 2 gathers telemetry samples, verifying that the statistical median error rate returns to zero percent."),
        ("seg10_postmortem.mp3", "With SLOs fully restored, Sanctigraph marks the incident resolved. It automatically generates a comprehensive, blameless Markdown post-mortem detailing timeline, root cause, preventative action items, and financial loss averted."),
        ("seg11_outro.mp3", "Sanctigraph compresses a 49-minute scramble into a 40-second deterministic recovery. Fully autonomous, cryptographically guarded, and production ready. Thank you.")
    ]

    print(">>> 1. Generating audio narration segments with edge-tts...")
    concat_list = os.path.join(build_dir, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as clist:
        for fname, text in segments:
            fpath = os.path.join(build_dir, fname)
            cmd = ["edge-tts", "--voice", "en-US-ChristopherNeural", "--text", text, "--write-media", fpath]
            subprocess.run(cmd, check=True)
            clist.write(f"file '{fname}'\n")

    full_audio = os.path.join(build_dir, "full_narration.mp3")
    print(">>> 2. Merging audio segments...")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        full_audio
    ], check=True)

    print(">>> 3. Resetting demo state on local server...")
    try:
        httpx.post("http://127.0.0.1:8000/api/demo/clear", timeout=3.0)
    except Exception as e:
        print("Clear warning:", e)

    print(">>> 4. Starting high-definition Playwright browser capture...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="msedge",
            headless=True,
            args=[
                "--start-maximized",
                "--hide-scrollbars",
                "--disable-infobars",
                "--no-sandbox"
            ]
        )
        context = browser.new_context(
            record_video_dir=raw_dir,
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page = context.new_page()

        print("[0.0s] Loading cockpit...")
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page.evaluate("document.body.style.zoom = '1.15'")
        page.wait_for_timeout(2000)

        # Seg 1: Intro (0s to 11.5s)
        print("[2.0s] Seg 1: Exploring cockpit baseline...")
        page.mouse.move(300, 30)
        page.wait_for_timeout(2000)
        page.mouse.move(500, 110)
        page.wait_for_timeout(3000)
        page.mouse.move(960, 220)
        page.wait_for_timeout(4500)

        # Seg 2: Problem (11.5s to 27.7s)
        print("[11.5s] Seg 2: Touring 9-node DAG architecture...")
        page.mouse.move(400, 260)
        page.wait_for_timeout(3000)
        page.mouse.move(960, 260)
        page.wait_for_timeout(3000)
        page.mouse.move(1400, 260)
        page.wait_for_timeout(3000)
        page.mouse.move(960, 500)
        page.wait_for_timeout(4000)
        page.mouse.move(1350, 35)
        page.wait_for_timeout(3200)

        # Seg 3: Trigger Fault (27.7s to 36.0s)
        print("[27.7s] Seg 3: Triggering 504 Pool Starvation...")
        trigger_btn = page.locator("button:has-text('504 Pool Starvation')")
        if trigger_btn.count() > 0:
            trigger_btn.first.hover()
            page.wait_for_timeout(1500)
            trigger_btn.first.click()
            print("Clicked 504 Pool Starvation button!")
        else:
            httpx.post("http://127.0.0.1:8000/api/demo/trigger", json={"fault": "connection_starvation"})
        page.wait_for_timeout(6800)

        # Seg 4: Telemetry surge & Nodes 1-2 (36.0s to 57.4s)
        print("[36.0s] Seg 4: Telemetry surge & autonomous engagement...")
        page.mouse.move(400, 110)
        page.wait_for_timeout(5000)
        page.mouse.move(250, 260)
        page.wait_for_timeout(5000)
        page.mouse.move(450, 260)
        page.wait_for_timeout(5000)
        page.mouse.move(500, 500)
        page.wait_for_timeout(6400)

        # Seg 5: Sanitizer & Prompt Injection (57.4s to 74.1s)
        print("[57.4s] Seg 5: Node 3 Telemetry Sanitizer...")
        page.mouse.move(650, 260)
        page.wait_for_timeout(5000)
        page.mouse.move(960, 600)
        page.wait_for_timeout(6000)
        page.mouse.move(850, 260)
        page.wait_for_timeout(5700)

        # Seg 6: RCA & Blast Radius (74.1s to 91.0s)
        print("[74.1s] Seg 6: RCA & Blast Radius...")
        page.mouse.move(850, 260)
        page.wait_for_timeout(4000)
        page.mouse.move(1050, 260)
        page.wait_for_timeout(4000)
        page.mouse.move(500, 650)
        page.wait_for_timeout(8900)

        # Seg 7: HMAC Gate (91.0s to 111.7s)
        print("[91.0s] Seg 7: Cryptographic Approval Gate & Slack card...")
        page.mouse.move(1250, 260)
        page.wait_for_timeout(4000)
        page.mouse.move(1450, 260)
        page.wait_for_timeout(4000)
        approve_btn = page.locator("button:has-text('APPROVE')")
        if approve_btn.count() > 0:
            approve_btn.first.scroll_into_view_if_needed()
            page.wait_for_timeout(2000)
            approve_btn.first.hover()
        page.wait_for_timeout(10700)

        # Seg 8: Execution (111.7s to 126.6s)
        print("[111.7s] Seg 8: Approving remediation...")
        if approve_btn.count() > 0:
            approve_btn.first.click()
            print("Clicked Approve button!")
        page.wait_for_timeout(3000)
        page.mouse.move(960, 360)
        page.wait_for_timeout(5000)
        page.mouse.move(960, 650)
        page.wait_for_timeout(6900)

        # Seg 9: Canary (126.6s to 145.0s)
        print("[126.6s] Seg 9: Adaptive 2-Phase Canary observation...")
        page.mouse.move(1160, 360)
        page.wait_for_timeout(6000)
        page.mouse.move(400, 110)
        page.wait_for_timeout(6000)
        page.mouse.move(1160, 360)
        page.wait_for_timeout(6400)

        # Seg 10: Post-Mortem (145.0s to 160.8s)
        print("[145.0s] Seg 10: Blameless Post-Mortem review...")
        pm_btn = page.locator("button:has-text('Export MD'), button:has-text('Post-Mortem')")
        if pm_btn.count() > 0:
            pm_btn.first.hover()
            page.wait_for_timeout(1500)
            pm_btn.first.click()
            page.wait_for_timeout(4000)
            page.mouse.wheel(0, 300)
            page.wait_for_timeout(4000)
            page.mouse.wheel(0, -300)
            page.wait_for_timeout(3000)
        else:
            page.wait_for_timeout(15800)
        page.wait_for_timeout(3300)

        # Seg 11: Outro (160.8s to 173.1s)
        print("[160.8s] Seg 11: Final Outro...")
        page.mouse.move(960, 150)
        page.wait_for_timeout(4000)
        page.mouse.move(960, 260)
        page.wait_for_timeout(8300)

        print("[173.1s] Browser capture complete.")
        context.close()
        browser.close()

    print(">>> 5. Finding captured video file...")
    raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".webm")]
    raw_files.sort(key=lambda x: os.path.getsize(os.path.join(raw_dir, x)), reverse=True)
    chosen_video = os.path.join(raw_dir, raw_files[0])
    print("Using raw video:", chosen_video, f"({os.path.getsize(chosen_video)} bytes)")

    print(">>> 6. Muxing final high-bitrate, enhanced-contrast 1080p MP4...")
    output_mp4 = "sanctigraph_demo_voiceover.mp4"
    mux_cmd = [
        "ffmpeg", "-y",
        "-i", chosen_video,
        "-i", full_audio,
        "-vf", "eq=contrast=1.06:brightness=0.03:saturation=1.18,scale=1920:1080:flags=lanczos",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-b:v", "6M",
        "-maxrate", "8M",
        "-bufsize", "12M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        output_mp4
    ]
    subprocess.run(mux_cmd, check=True)
    print(">>> SUCCESS: Created", output_mp4, f"({os.path.getsize(output_mp4) / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    build_hd_demo()
