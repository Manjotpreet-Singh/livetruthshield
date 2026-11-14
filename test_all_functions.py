import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "http://127.0.0.1:5000"

def log_test(name, success, details=""):
    mark = "[PASS]" if success else "[FAIL]"
    print(f"{mark} | {name}: {details}")
    return success

def run_tests():
    print("=" * 65)
    print("      LIVETRUTH SHIELD // COMPREHENSIVE SYSTEM TEST SUITE      ")
    print("=" * 65)

    results = []

    # 1. Health Endpoint
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            ok = resp.status == 200 and data.get("status") == "online" and data.get("thinking_level") == "HIGH"
            results.append(log_test("Health Check (/api/health)", ok, f"status={data.get('status')}, model={data.get('model')}, thinking={data.get('thinking_level')}"))
    except Exception as e:
        results.append(log_test("Health Check (/api/health)", False, str(e)))

    # 2. Web Dashboard Root (/)
    try:
        req = urllib.request.Request(f"{BASE_URL}/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            ok = resp.status == 200 and "LiveTruth Shield" in html and "scoreCircleProgress" in html and "assistantChat" in html
            results.append(log_test("Web Console UI (/)", ok, f"HTTP {resp.status}, length={len(html)} chars"))
    except Exception as e:
        results.append(log_test("Web Console UI (/)", False, str(e)))

    # 3. Presentation Slide Deck (/presentation)
    try:
        req = urllib.request.Request(f"{BASE_URL}/presentation")
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            ok = resp.status == 200 and "LiveTruth Shield // Presentation Deck" in html
            results.append(log_test("Presentation Deck (/presentation)", ok, f"HTTP {resp.status}, length={len(html)} chars"))
    except Exception as e:
        results.append(log_test("Presentation Deck (/presentation)", False, str(e)))

    # 4. PowerPoint File Download (/LiveTruth_Shield_Presentation.pptx)
    try:
        req = urllib.request.Request(f"{BASE_URL}/LiveTruth_Shield_Presentation.pptx")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            ok = resp.status == 200 and len(data) > 10000
            results.append(log_test("PPTX Download Endpoint", ok, f"HTTP {resp.status}, size={len(data)} bytes"))
    except Exception as e:
        results.append(log_test("PPTX Download Endpoint", False, str(e)))

    # 5. Creator Veracity Index (/api/channel-score)
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/channel-score?channel=Veritasium")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            ok = resp.status == 200 and "veracity_score" in data and "rating" in data
            results.append(log_test("Creator Veracity Index (/api/channel-score)", ok, f"Channel: {data.get('channel')}, Score: {data.get('veracity_score')}%, Rating: {data.get('rating')}"))
    except Exception as e:
        results.append(log_test("Creator Veracity Index (/api/channel-score)", False, str(e)))

    # 6. Ask Gemini In-Player Assistant (POST /api/ask)
    try:
        payload = json.dumps({
            "question": "What is the capital of South Korea?",
            "video_id": "test_video",
            "title": "Geographic Facts"
        }).encode('utf-8')
        req = urllib.request.Request(f"{BASE_URL}/api/ask", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            ok = resp.status == 200 and data.get("success") is True and len(data.get("answer", "")) > 10
            results.append(log_test("Ask Gemini Assistant (POST /api/ask)", ok, f"Model: {data.get('model')}, Answer: {data.get('answer')[:65]}..."))
    except Exception as e:
        results.append(log_test("Ask Gemini Assistant (POST /api/ask)", False, str(e)))

    # 7. Ask Gemini GET query fallback (GET /api/ask?q=...)
    try:
        q_enc = urllib.parse.quote("Is the earth flat?")
        req = urllib.request.Request(f"{BASE_URL}/api/ask?q={q_enc}")
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            ok = resp.status == 200 and data.get("success") is True
            results.append(log_test("Ask Gemini Assistant (GET /api/ask)", ok, f"Answer: {data.get('answer')[:65]}..."))
    except Exception as e:
        results.append(log_test("Ask Gemini Assistant (GET /api/ask)", False, str(e)))

    # 8. Video Fact-Checking Pipeline (/api/check) with Sample Demo
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/check?v=demo&title=Tom+Holland+Podcast")
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            cards = data.get("cards", [])
            has_fallacy = any("fallacy" in c for c in cards)
            has_consensus = any("consensus" in c for c in cards)
            has_abstract = any("abstractPreview" in c for c in cards)
            ok = resp.status == 200 and len(cards) > 0 and has_fallacy and has_consensus
            results.append(log_test("Fact-Checking Pipeline (/api/check)", ok, f"Score: {data.get('score')}%, Claims: {len(cards)}, Fallacies={has_fallacy}, Consensus={has_consensus}, Abstracts={has_abstract}"))
    except Exception as e:
        results.append(log_test("Fact-Checking Pipeline (/api/check)", False, str(e)))

    # 9. Video Fact-Checking Pipeline Empty / Non-Video State
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/check?v=&title=")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            ok = resp.status == 200 and data.get("score") == 0 and len(data.get("cards", [])) == 0
            results.append(log_test("Empty Video Input Handling", ok, f"Correctly returns clean neutral state (score=0, 0 cards)"))
    except Exception as e:
        results.append(log_test("Empty Video Input Handling", False, str(e)))

    # 10. Local Video Check Endpoint (/api/check-local)
    try:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test_clip.mp4"\r\n'
            f"Content-Type: video/mp4\r\n\r\n"
            f"fake video content for test\r\n"
            f"--{boundary}--\r\n"
        ).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}/api/check-local",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            ok = resp.status == 200 and "score" in data and "cards" in data
            results.append(log_test("Local Video Upload (/api/check-local)", ok, f"Score: {data.get('score')}%, Claims: {len(data.get('cards', []))}"))
    except Exception as e:
        results.append(log_test("Local Video Upload (/api/check-local)", False, str(e)))

    # 11. Chrome Extension Manifest & File Structure Validation
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ext_dir = os.path.join(base_dir, "extension")
    manifest_path = os.path.join(ext_dir, "manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        has_mv3 = manifest.get("manifest_version") == 3
        has_sw = "service_worker" in manifest.get("background", {})
        has_cs = len(manifest.get("content_scripts", [])) > 0
        ok = has_mv3 and has_sw and has_cs
        results.append(log_test("Extension Manifest (Manifest v3)", ok, f"Name: {manifest.get('name')}, Version: {manifest.get('version')}"))
    except Exception as e:
        results.append(log_test("Extension Manifest (Manifest v3)", False, str(e)))

    # 12. Chrome Extension Background Script
    bg_path = os.path.join(ext_dir, "background.js")
    try:
        with open(bg_path, "r", encoding="utf-8") as f:
            bg_code = f.read()
        handles_check = "checkVideo" in bg_code
        handles_ask = "askQuestion" in bg_code
        handles_channel = "getChannelScore" in bg_code
        ok = handles_check and handles_ask and handles_channel
        results.append(log_test("Extension Background Service Worker", ok, f"Handlers: checkVideo={handles_check}, askQuestion={handles_ask}, getChannelScore={handles_channel}"))
    except Exception as e:
        results.append(log_test("Extension Background Service Worker", False, str(e)))

    # 13. Chrome Extension Content Script Functions Check
    content_path = os.path.join(ext_dir, "content.js")
    try:
        with open(content_path, "r", encoding="utf-8") as f:
            code = f.read()
        has_heatmap = "injectYouTubeScrubberHeatmap" in code
        has_autopause = "showAutoPauseBanner" in code
        has_ask = "sendExtensionQuestion" in code
        has_channel_score = "getChannelScore" in code
        has_fallacy = "lt-fallacy-badge" in code
        has_consensus = "lt-consensus-badge" in code
        has_abstract = "lt-abstract-details" in code
        ok = all([has_heatmap, has_autopause, has_ask, has_channel_score, has_fallacy, has_consensus, has_abstract])
        results.append(log_test("Extension Content Script Capabilities", ok, f"Heatmap={has_heatmap}, AutoPause={has_autopause}, Assistant={has_ask}, CreatorVeracity={has_channel_score}, Badges={has_fallacy and has_consensus}"))
    except Exception as e:
        results.append(log_test("Extension Content Script Capabilities", False, str(e)))

    # 14. Presentation Slide Deck Integrity Check
    pres_file = os.path.join(base_dir, "presentation.html")
    p_exists = os.path.exists(pres_file) and os.path.getsize(pres_file) > 10000
    results.append(log_test("Presentation Deck Availability", p_exists, f"presentation.html={os.path.getsize(pres_file) if p_exists else 0} bytes"))

    print("=" * 65)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"TEST RESULTS: {passed} / {total} PASSED")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
