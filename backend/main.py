import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import json



import asyncio



import threading



import time



import urllib.parse
import hashlib
import re



import webbrowser



from fastapi import FastAPI, Query, HTTPException, File, UploadFile, Request



from fastapi.responses import HTMLResponse, Response, FileResponse



from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles



from youtube_transcript_api import YouTubeTranscriptApi



from dotenv import load_dotenv
import httpx
try:
    import transcriber
except Exception as _tr_err:
    transcriber = None

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

import sys
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import ai_engine

Features_Available = ai_engine.Features_Available
app = FastAPI(title="LiveTruth Shield API", version="1.0.0")

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")







# High-Performance In-Memory Verification Cache (Instant zero-latency responses for repeated videos)



CACHE_DB_PATH = os.path.join(backend_dir, "cache_history.json")
try:
    with open(CACHE_DB_PATH, "r", encoding="utf-8") as _cf:
        VERIFICATION_CACHE = json.load(_cf)
except Exception:
    VERIFICATION_CACHE = {}

MAX_CACHE_SIZE = 150

def save_cache_to_disk():
    try:
        with open(CACHE_DB_PATH, "w", encoding="utf-8") as _cf:
            json.dump(VERIFICATION_CACHE, _cf, ensure_ascii=False)
    except Exception:
        pass











app.add_middleware(



    CORSMiddleware,



    allow_origins=["*"],



    allow_credentials=True,



    allow_methods=["*"],



    allow_headers=["*"],



)







GEMINI_API_KEY = ai_engine.GEMINI_API_KEY
client = ai_engine.genai_client







def extract_video_id_and_title(url_or_id: str, title: str = "") -> tuple[str, str]:
    if not url_or_id:
        return "", title

    url_or_id = urllib.parse.unquote(url_or_id).strip()
    clean = url_or_id.rstrip("/")

    if clean in ["https://www.youtube.com", "http://www.youtube.com", "youtube.com", "https://m.youtube.com", "http://localhost:5000", "http://127.0.0.1:5000"]:
        return "", title

    # 1. Standard YouTube URL patterns
    if "v=" in url_or_id:
        v = url_or_id.split("v=")[1].split("&")[0].split("#")[0]
        if len(v) >= 6:
            return v, title
    if "youtu.be/" in url_or_id:
        v = url_or_id.split("youtu.be/")[1].split("?")[0].split("&")[0]
        if len(v) >= 6:
            return v, title
    if "shorts/" in url_or_id:
        v = url_or_id.split("shorts/")[1].split("?")[0].split("&")[0]
        if len(v) >= 6:
            return v, title
    if "embed/" in url_or_id:
        v = url_or_id.split("embed/")[1].split("?")[0].split("&")[0]
        if len(v) >= 6:
            return v, title

    # 1.5 Instagram Reel / Video pattern
    if "instagram.com/reel/" in url_or_id or "instagram.com/reels/" in url_or_id or "/reel/" in url_or_id:
        p = url_or_id.split("reel/")[1] if "reel/" in url_or_id else url_or_id.split("reels/")[1]
        shortcode = p.split("?")[0].split("/")[0].split("&")[0]
        if shortcode:
            final_title = title if (title and title.lower() not in ["instagram reel", "live video", ""]) else f"Instagram Reel {shortcode}"
            return f"ig_{shortcode}", final_title

    # 2. Local file or direct media file detection
    is_local_or_media = (
        url_or_id.lower().startswith("file:") or
        any(url_or_id.lower().endswith(ext) for ext in [".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv", ".m4v", ".mp3", ".wav"]) or
        (':\\' in url_or_id and not url_or_id.lower().startswith(("http://", "https://")))
    )

    if is_local_or_media:
        path_part = re.sub(r"^file:///?", "", url_or_id)
        basename = os.path.basename(path_part.replace("/", os.sep).replace("\\", os.sep))
        clean_name = re.sub(r"^(vidssave\.com|y2mate\.is|savefrom\.net|ssyoutube|y2mate|yt1s|snapsave)\s*", "", basename, flags=re.I)
        clean_name = re.sub(r"\.(mp4|mkv|mov|webm|avi|flv|m4v|mp3|wav)$", "", clean_name, flags=re.I)
        clean_name = re.sub(r"[\_\.]+", " ", clean_name)
        clean_name = re.sub(r"\s+", " ", clean_name).strip()

        vid_id = "local_" + hashlib.md5(basename.lower().encode("utf-8")).hexdigest()[:10]
        final_title = title if (title and title.lower() not in ["live video", "youtube", "video", ""]) else clean_name
        return vid_id, final_title

    # 3. Direct 11-char YouTube ID fallback
    if len(clean) <= 15 and " " not in clean and "/" not in clean and "\\" not in clean:
        return clean, title

    # 4. If title or string has meaningful text
    if clean and len(clean) > 3 and not clean.startswith("http"):
        vid_id = "topic_" + hashlib.md5(clean.lower().encode("utf-8")).hexdigest()[:10]
        final_title = title if (title and title.lower() not in ["live video", "youtube", "video", ""]) else clean
        return vid_id, final_title

    return "", title


def extract_video_id(url_or_id: str) -> str:
    vid, _ = extract_video_id_and_title(url_or_id, "")
    return vid

@app.get("/", response_class=HTMLResponse)
def root_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LiveTruth Shield // Universal Real-Time AI Fact-Checker</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%233B82F6%22 stroke-width=%222.2%22><path d=%22M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z%22/><path d=%22M10 15.5l-3.5-3.5 1.41-1.41L10 12.67l5.59-5.59L17 8.5l-7 7z%22 fill=%22%233B82F6%22/></svg>">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            color-scheme: dark;
            --bg: #07090E;
            --bg-elevated: #0C1019;
            --surface: #111624;
            --surface-hover: #161D30;
            --surface-card: rgba(17, 22, 36, 0.75);
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --border-glow: rgba(59, 130, 246, 0.35);
            --accent: #3B82F6;
            --accent-glow: #60A5FA;
            --accent-purple: #8B5CF6;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --text-dim: #64748B;
            --green: #10B981;
            --green-glow: rgba(16, 185, 129, 0.2);
            --red: #EF4444;
            --red-glow: rgba(239, 68, 68, 0.2);
            --yellow: #F59E0B;
            --yellow-glow: rgba(245, 158, 11, 0.2);
            --sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --mono: 'JetBrains Mono', monospace;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #06090e;
            background-image: 
                url('/static/dashboard_bg.jpg'),
                radial-gradient(ellipse 70% 50% at 50% 100%, #0d2818, transparent),
                radial-gradient(ellipse 80% 50% at 50% -20%, rgba(147, 51, 234, 0.12), transparent);
            background-size: cover;
            background-position: center bottom;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: var(--text-main);
            font-family: var(--sans);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        /* 1. Cyber Navigation Header */
        header {
            background: rgba(7, 11, 19, 0.7);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding: 12px 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: var(--text-main);
        }

        .brand-icon-box {
            width: 34px;
            height: 34px;
            border-radius: 9px;
            background: rgba(147, 51, 234, 0.15);
            border: 1px solid rgba(147, 51, 234, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 14px rgba(147, 51, 234, 0.35);
        }

        .brand-title {
            font-weight: 700;
            font-size: 16.5px;
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #FFFFFF;
        }

        .brand-badge {
            background: rgba(147, 51, 234, 0.2);
            color: #C084FC;
            font-size: 10.5px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 9999px;
            border: 1px solid rgba(147, 51, 234, 0.45);
            font-family: var(--mono);
            letter-spacing: 0.5px;
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .model-select-wrap {
            position: relative;
            display: flex;
            align-items: center;
        }

        .model-dropdown {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #E2E8F0;
            font-family: var(--sans);
            font-size: 11.5px;
            font-weight: 500;
            padding: 6px 14px;
            border-radius: 9999px;
            outline: none;
            cursor: pointer;
            transition: all 0.2s ease;
            backdrop-filter: blur(10px);
        }
        .model-dropdown:hover {
            border-color: rgba(168, 85, 247, 0.5);
            background: rgba(22, 29, 48, 0.85);
        }
        .model-dropdown option {
            background: #0C1019;
            color: #F8FAFC;
            font-family: var(--sans);
            padding: 6px;
        }

        /* Settings Modal */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.78);
            backdrop-filter: blur(8px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 99999;
        }
        .modal-card {
            background: #0D121F;
            border: 1px solid rgba(59, 130, 246, 0.35);
            border-radius: 14px;
            width: 92%;
            max-width: 540px;
            padding: 24px 28px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.8), 0 0 30px rgba(59,130,246,0.15);
            animation: modalFadeIn 0.2s ease-out;
        }
        @keyframes modalFadeIn {
            from { opacity: 0; transform: translateY(-12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }
        .modal-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 17px;
            font-weight: 700;
            color: #F8FAFC;
        }
        .modal-close-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 18px;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 6px;
        }
        .modal-close-btn:hover {
            color: #FFF;
            background: rgba(255,255,255,0.08);
        }
        .modal-desc {
            font-size: 12.5px;
            color: var(--text-muted);
            line-height: 1.45;
            margin-bottom: 18px;
        }
        .config-group {
            margin-bottom: 14px;
        }
        .config-group label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 5px;
        }
        .key-link {
            font-size: 11px;
            color: #60A5FA;
            text-decoration: none;
        }
        .key-link:hover { text-decoration: underline; }
        .input-with-toggle {
            display: flex;
            align-items: center;
            position: relative;
        }
        .input-with-toggle input, .config-group input[type="text"], .config-select {
            width: 100%;
            background: #131929;
            border: 1px solid var(--border);
            color: #F8FAFC;
            font-family: var(--mono);
            font-size: 12px;
            padding: 8px 12px;
            border-radius: 8px;
            outline: none;
            transition: all 0.2s ease;
        }
        .input-with-toggle input:focus, .config-group input[type="text"]:focus, .config-select:focus {
            border-color: #3B82F6;
            box-shadow: 0 0 10px rgba(59,130,246,0.25);
        }
        .input-with-toggle input { padding-right: 38px; }
        .toggle-pw-btn {
            position: absolute;
            right: 8px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 13px;
            opacity: 0.65;
        }
        .toggle-pw-btn:hover { opacity: 1; }
        .field-hint {
            font-size: 11px;
            color: var(--text-dim);
            margin-top: 4px;
        }
        .config-row {
            display: flex;
            gap: 12px;
            margin-bottom: 14px;
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 20px;
            padding-top: 14px;
            border-top: 1px solid var(--border);
        }
        .modal-btn {
            font-size: 12.5px;
            font-weight: 600;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .modal-btn.secondary {
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            color: var(--text-muted);
        }
        .modal-btn.secondary:hover {
            background: rgba(255,255,255,0.08);
            color: #FFF;
        }
        .modal-btn.primary {
            background: linear-gradient(135deg, #2563EB, #1D4ED8);
            border: 1px solid #3B82F6;
            color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(37,99,235,0.3);
        }
        .modal-btn.primary:hover {
            background: linear-gradient(135deg, #3B82F6, #2563EB);
        }

        .status-pill {
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 5px 14px;
            border-radius: 9999px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.4);
            font-size: 11px;
            font-family: var(--mono);
            font-weight: 700;
            color: #34D399;
            box-shadow: 0 0 12px rgba(16, 185, 129, 0.15);
        }

        .status-pulse {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 8px #10B981;
            animation: pulse-dot 1.8s infinite;
        }

        @keyframes pulse-dot {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 14px #10B981; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        .header-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #E2E8F0;
            border-radius: 9999px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
            backdrop-filter: blur(8px);
        }
        .header-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #FFFFFF;
            border-color: rgba(255, 255, 255, 0.25);
        }
        .header-btn.active {
            color: #A855F7;
            border-color: rgba(168, 85, 247, 0.5);
            background: rgba(168, 85, 247, 0.15);
        }

        /* 2. Main Content Layout */
        main {
            flex: 1;
            max-width: 980px;
            width: 100%;
            margin: 0 auto;
            padding: 40px 24px 60px;
        }

        .hero {
            text-align: center;
            margin-top: 24px;
            margin-bottom: 28px;
        }

        .hero h1 {
            font-size: 36px;
            font-weight: 800;
            letter-spacing: -0.025em;
            margin-bottom: 12px;
            color: #FFFFFF;
        }

        .hero h1 .gradient-purple {
            background: linear-gradient(135deg, #E879F9 0%, #A855F7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }

        .hero p {
            color: #94A3B8;
            font-size: 14.5px;
            max-width: 660px;
            margin: 0 auto 22px;
            line-height: 1.55;
        }

        /* Quick Demo Chips */
        .quick-chips {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 14px;
        }

        .chip-label {
            font-size: 11px;
            color: #64748B;
            font-family: var(--mono);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-right: 6px;
        }

        .demo-chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 9999px;
            padding: 6px 14px;
            font-size: 12px;
            color: #CBD5E1;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
            backdrop-filter: blur(8px);
        }
        .demo-chip:hover {
            background: rgba(147, 51, 234, 0.15);
            color: #FFFFFF;
            border-color: rgba(168, 85, 247, 0.45);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(147, 51, 234, 0.2);
        }

        /* 3. Modern Segmented Tab Switcher */
        .tabs {
            display: inline-flex;
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 4px;
            border-radius: 9999px;
            margin-bottom: 22px;
            backdrop-filter: blur(14px);
        }

        .tab-btn {
            background: transparent;
            border: 1px solid transparent;
            color: #94A3B8;
            font-family: var(--sans);
            font-size: 12.5px;
            font-weight: 500;
            padding: 7px 22px;
            border-radius: 9999px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 7px;
        }

        .tab-btn:hover {
            color: #FFFFFF;
        }

        .tab-btn.active {
            background: rgba(124, 58, 237, 0.25);
            border: 1px solid #7C3AED;
            color: #FFFFFF;
            font-weight: 600;
            box-shadow: 0 0 14px rgba(124, 58, 237, 0.35);
        }

        /* 4. Glowing Input Bar */
        .input-bar {
            max-width: 840px;
            width: 100%;
            margin: 0 auto 28px;
            background: rgba(10, 16, 26, 0.7);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(16, 185, 129, 0.45);
            box-shadow: 0 0 24px rgba(16, 185, 129, 0.15), 0 8px 32px rgba(0, 0, 0, 0.5);
            border-radius: 9999px;
            padding: 5px 6px 5px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .input-bar:focus-within {
            border-color: rgba(16, 185, 129, 0.75);
            box-shadow: 0 0 32px rgba(16, 185, 129, 0.3), 0 8px 36px rgba(0, 0, 0, 0.6);
        }

        .input-bar input,
        #videoUrl {
            flex: 1;
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #FFFFFF !important;
            font-family: var(--sans);
            font-size: 14px;
            outline: none !important;
            -webkit-appearance: none;
            appearance: none;
        }

        .input-bar input::placeholder,
        #videoUrl::placeholder {
            color: #64748B;
            opacity: 1;
        }

        /* Prevent Chrome white autofill and user agent white bar glitch */
        .input-bar input:-webkit-autofill,
        .input-bar input:-webkit-autofill:hover, 
        .input-bar input:-webkit-autofill:focus, 
        .input-bar input:-webkit-autofill:active,
        #videoUrl:-webkit-autofill {
            -webkit-box-shadow: 0 0 0 1000px #0a101a inset !important;
            -webkit-text-fill-color: #FFFFFF !important;
            box-shadow: 0 0 0 1000px #0a101a inset !important;
            transition: background-color 5000s ease-in-out 0s !important;
            caret-color: #FFFFFF !important;
        }

        .input-bar button,
        #btnAudit {
            background: linear-gradient(135deg, #9333EA, #7C3AED);
            color: #FFFFFF;
            border: none;
            border-radius: 9999px;
            padding: 10px 26px;
            font-family: var(--sans);
            font-weight: 600;
            font-size: 13.5px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 0 20px rgba(147, 51, 234, 0.45);
            display: inline-flex;
            align-items: center;
            gap: 7px;
            white-space: nowrap;
        }

        .input-bar button:hover,
        #btnAudit:hover {
            background: linear-gradient(135deg, #A855F7, #9333EA);
            box-shadow: 0 0 26px rgba(168, 85, 247, 0.65);
            transform: translateY(-1px);
        }

        .input-bar button:active,
        #btnAudit:active {
            transform: translateY(0);
        }

        /* Local File Dropzone */
        .upload-dropzone {
            display: none;
            border: 2px dashed rgba(255, 255, 255, 0.12);
            border-radius: 14px;
            padding: 34px 20px;
            text-align: center;
            background: var(--surface);
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 26px;
        }
        .upload-dropzone:hover {
            border-color: rgba(59, 130, 246, 0.5);
            background: rgba(59, 130, 246, 0.04);
        }
        .upload-icon {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: rgba(59, 130, 246, 0.12);
            color: var(--accent-glow);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 12px;
            font-size: 20px;
        }

        /* 5. Results Panel & Truth Intelligence */
        .panel {
            background: rgba(10, 16, 26, 0.75);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5), 0 0 30px rgba(147, 51, 234, 0.08);
            transition: all 0.3s ease;
        }

        /* Analytics Overview Banner */
        .analytics-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 18px;
            padding-bottom: 22px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }

        .score-block {
            display: flex;
            align-items: center;
            gap: 18px;
        }

        .score-circle {
            position: relative;
            width: 72px;
            height: 72px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .score-svg {
            transform: rotate(-90deg);
            width: 100%;
            height: 100%;
        }

        .score-svg circle {
            fill: none;
            stroke-width: 6;
            stroke-linecap: round;
        }

        .score-bg-circle {
            stroke: rgba(255, 255, 255, 0.08);
        }

        .score-val-circle {
            stroke: #10B981;
            stroke-dasharray: 188;
            stroke-dashoffset: 188;
            transition: stroke-dashoffset 1s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.4s ease;
        }

        .score-number {
            position: absolute;
            font-family: var(--mono);
            font-size: 19px;
            font-weight: 700;
            color: #FFFFFF;
        }

        .score-meta h3 {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.01em;
            margin-bottom: 4px;
        }

        .score-meta p {
            font-size: 12.5px;
            color: var(--text-dim);
            font-family: var(--mono);
        }

        /* Stat Metrics Row */
        .metrics-row {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .metric-badge {
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: 9px;
            padding: 8px 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-family: var(--mono);
            transition: all 0.2s ease;
        }

        .metric-badge.false {
            border-color: rgba(239, 68, 68, 0.3);
            background: rgba(239, 68, 68, 0.08);
            color: #F87171;
        }

        .metric-badge.misleading {
            border-color: rgba(245, 158, 11, 0.3);
            background: rgba(245, 158, 11, 0.08);
            color: #FBBF24;
        }

        .metric-badge.verified {
            border-color: rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.08);
            color: #34D399;
        }

        /* Action Toolbar */
        .action-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 22px;
        }

        .filter-group {
            display: flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-elevated);
            padding: 3px;
            border-radius: 10px;
            border: 1px solid var(--border);
        }

        .filter-btn {
            background: none;
            border: none;
            color: var(--text-dim);
            font-size: 12px;
            font-weight: 500;
            padding: 5px 12px;
            border-radius: 7px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .filter-btn.active {
            background: var(--surface);
            color: #FFFFFF;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .share-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .export-btn {
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            color: var(--text-muted);
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
        }
        .export-btn:hover {
            color: #FFFFFF;
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }

        /* Intel Summary Box */
        .intel-box {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.06), rgba(139, 92, 246, 0.04));
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 24px;
            font-size: 13.5px;
            line-height: 1.6;
            color: #E2E8F0;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }

        .intel-box-icon {
            font-size: 18px;
            flex-shrink: 0;
            margin-top: 1px;
        }

        /* 6. High-End Fact Card Design */
        #cardsList {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .card-item {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px 20px;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            overflow: hidden;
        }

        .card-item:hover {
            transform: translateY(-2px);
            border-color: var(--border-hover);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
        }

        .card-item::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            border-radius: 4px 0 0 4px;
        }

        .card-item.FALSE {
            border-color: rgba(239, 68, 68, 0.22);
            background: linear-gradient(180deg, rgba(239, 68, 68, 0.04), var(--surface) 35%);
        }
        .card-item.FALSE::before { background: #EF4444; box-shadow: 0 0 10px #EF4444; }

        .card-item.MISLEADING {
            border-color: rgba(245, 158, 11, 0.22);
            background: linear-gradient(180deg, rgba(245, 158, 11, 0.04), var(--surface) 35%);
        }
        .card-item.MISLEADING::before { background: #F59E0B; box-shadow: 0 0 10px #F59E0B; }

        .card-item.VERIFIED {
            border-color: rgba(16, 185, 129, 0.22);
            background: linear-gradient(180deg, rgba(16, 185, 129, 0.04), var(--surface) 35%);
        }
        .card-item.VERIFIED::before { background: #10B981; box-shadow: 0 0 10px #10B981; }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }

        .verdict-tag {
            font-size: 11px;
            font-weight: 700;
            font-family: var(--mono);
            letter-spacing: 0.04em;
            padding: 3px 9px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .verdict-tag.FALSE {
            background: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .verdict-tag.MISLEADING {
            background: rgba(245, 158, 11, 0.15);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .verdict-tag.VERIFIED {
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .timestamp-pill {
            font-family: var(--mono);
            font-size: 11px;
            color: var(--text-dim);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 2px 7px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .quote-box {
            font-family: var(--mono);
            font-size: 12.5px;
            color: #E2E8F0;
            background: rgba(0, 0, 0, 0.25);
            border-left: 2px solid rgba(255, 255, 255, 0.15);
            padding: 8px 12px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 12px;
            line-height: 1.5;
        }

        .explanation-text {
            font-size: 13.5px;
            line-height: 1.6;
            color: #CBD5E1;
            margin-bottom: 14px;
        }

        /* Authority & Evidence Box */
        .evidence-dossier {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 10px 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
        }

        .evidence-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 6px;
        }

        .authority-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
            color: var(--text-main);
        }

        .authority-link {
            color: var(--accent-glow);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: opacity 0.15s ease;
        }
        .authority-link:hover {
            text-decoration: underline;
        }

        .paper-title {
            color: var(--text-dim);
            font-family: var(--mono);
            font-size: 11px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 100%;
        }

        /* Logical Fallacy & Scientific Consensus Badges */
        .fallacy-tag {
            font-size: 10px;
            font-weight: 700;
            font-family: var(--mono);
            background: rgba(239, 68, 68, 0.12);
            color: #FCA5A5;
            border: 1px solid rgba(239, 68, 68, 0.35);
            padding: 2px 7px;
            border-radius: 5px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .consensus-tag {
            font-size: 10px;
            font-weight: 700;
            font-family: var(--mono);
            padding: 2px 7px;
            border-radius: 5px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .consensus-tag.universal {
            background: rgba(16, 185, 129, 0.12);
            color: #6EE7B7;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .consensus-tag.debate {
            background: rgba(245, 158, 11, 0.12);
            color: #FCD34D;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .consensus-tag.pseudoscience {
            background: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        /* Abstract Accordion */
        .abstract-accordion {
            margin-top: 8px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 6px;
            overflow: hidden;
        }
        .abstract-accordion summary {
            padding: 6px 10px;
            font-size: 11px;
            font-weight: 600;
            color: var(--accent-glow);
            cursor: pointer;
            user-select: none;
            outline: none;
        }
        .abstract-accordion summary:hover {
            background: rgba(255, 255, 255, 0.04);
        }
        .abstract-content {
            padding: 8px 12px;
            font-size: 11.5px;
            line-height: 1.5;
            color: var(--text-dim);
            border-top: 1px solid rgba(255, 255, 255, 0.04);
        }

        /* Ask Gemini Assistant Section */
        .assistant-section {
            margin-top: 24px;
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.45), rgba(15, 23, 42, 0.65));
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 14px;
            padding: 18px;
        }
        .assistant-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }
        .assistant-title {
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .assistant-badge {
            font-size: 10px;
            font-family: var(--mono);
            color: var(--accent-glow);
            background: rgba(59, 130, 246, 0.15);
            padding: 2px 7px;
            border-radius: 4px;
            font-weight: 600;
        }
        .assistant-chips {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .assistant-chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            color: var(--text-dim);
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .assistant-chip:hover {
            color: var(--text-main);
            border-color: var(--accent-glow);
            background: rgba(59, 130, 246, 0.1);
        }
        .assistant-chat {
            max-height: 200px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 12px;
            padding-right: 4px;
        }
        .chat-bubble {
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 12.5px;
            line-height: 1.5;
            max-width: 90%;
        }
        .chat-bubble.user {
            align-self: flex-end;
            background: #2563EB;
            color: #FFFFFF;
        }
        .chat-bubble.bot {
            align-self: flex-start;
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid var(--border);
            color: #E2E8F0;
        }
        .assistant-input-row {
            display: flex;
            gap: 8px;
        }
        .assistant-input {
            flex: 1;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 12px;
            color: #FFFFFF;
            font-size: 13px;
            outline: none;
        }
        .assistant-input:focus {
            border-color: var(--accent-glow);
        }
        .assistant-send-btn {
            background: var(--accent-glow);
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 0 16px;
            font-weight: 600;
            font-size: 12.5px;
            cursor: pointer;
            transition: opacity 0.15s ease;
        }
        .assistant-send-btn:hover { opacity: 0.9; }

        /* Auto-Pause Warning Banner */
        .autopause-btn {
            background: rgba(147, 51, 234, 0.2);
            border: 1px solid rgba(168, 85, 247, 0.5);
            color: #F3E8FF;
            padding: 6px 16px;
            border-radius: 9999px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
            box-shadow: 0 0 14px rgba(147, 51, 234, 0.25);
            backdrop-filter: blur(8px);
        }
        .autopause-btn:hover {
            background: rgba(147, 51, 234, 0.3);
            border-color: #A855F7;
            color: #FFFFFF;
        }
        .autopause-btn.active {
            background: rgba(147, 51, 234, 0.25);
            border-color: #A855F7;
            color: #FFFFFF;
            box-shadow: 0 0 18px rgba(168, 85, 247, 0.35);
        }

        /* Toast notification */
        #lt-toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(30px);
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(59, 130, 246, 0.4);
            color: #FFFFFF;
            padding: 10px 22px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 500;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            opacity: 0;
            pointer-events: none;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        #lt-toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }

        /* Loading Skeleton */
        .skeleton-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            position: relative;
            overflow: hidden;
        }

        .skeleton-card::after {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.04), transparent);
            animation: skeleton-shimmer 1.5s infinite;
        }

        @keyframes skeleton-shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .skeleton-line {
            height: 12px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 6px;
        }
        .skeleton-line.short { width: 40%; }
        .skeleton-line.medium { width: 70%; }


        /* ========================================================= */
        /* STRONGLY RESPONSIVE MOBILE & TABLET ADAPTATIONS (<= 768px) */
        /* ========================================================= */
        @media (max-width: 768px) {
            header {
                padding: 12px 16px !important;
                flex-wrap: wrap !important;
                gap: 10px !important;
            }
            .brand-title {
                font-size: 15px !important;
            }
            .header-meta {
                gap: 8px !important;
                flex-wrap: wrap !important;
            }
            .status-pill {
                font-size: 10.5px !important;
                padding: 4px 8px !important;
            }
            .header-btn {
                padding: 5px 8px !important;
                font-size: 11px !important;
            }
            main {
                padding: 20px 14px 50px !important;
                max-width: 100% !important;
            }
            .hero h1 {
                font-size: 24px !important;
                line-height: 1.2 !important;
            }
            .hero p {
                font-size: 13px !important;
                margin-bottom: 14px !important;
            }
            .quick-chips {
                gap: 6px !important;
                justify-content: flex-start !important;
            }
            .demo-chip {
                font-size: 11px !important;
                padding: 4px 10px !important;
            }
            .tabs {
                width: 100% !important;
                display: flex !important;
                justify-content: stretch !important;
            }
            .tab-btn {
                flex: 1 !important;
                justify-content: center !important;
                padding: 8px 10px !important;
                font-size: 12px !important;
            }
            .input-bar {
                flex-direction: column !important;
                padding: 12px !important;
                gap: 12px !important;
                border-radius: 14px !important;
                align-items: stretch !important;
            }
            .input-bar input,
            #videoUrl {
                width: 100% !important;
                font-size: 14px !important;
                padding: 4px 0 !important;
            }
            .input-bar button {
                width: 100% !important;
                justify-content: center !important;
                padding: 11px 16px !important;
                font-size: 14px !important;
                border-radius: 9px !important;
            }
            .panel {
                padding: 16px 14px !important;
                border-radius: 14px !important;
            }
            .analytics-header {
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 16px !important;
            }
            .score-block {
                width: 100% !important;
            }
            .metrics-row {
                width: 100% !important;
                display: grid !important;
                grid-template-columns: repeat(3, 1fr) !important;
                gap: 6px !important;
            }
            .metric-badge {
                justify-content: center !important;
                padding: 6px 4px !important;
                font-size: 11px !important;
            }
            .action-toolbar {
                flex-direction: column !important;
                align-items: stretch !important;
                gap: 12px !important;
            }
            .filter-group {
                display: flex !important;
                width: 100% !important;
                justify-content: space-between !important;
            }
            .filter-btn {
                flex: 1 !important;
                text-align: center !important;
                padding: 6px 4px !important;
                font-size: 11px !important;
            }
            .share-actions {
                width: 100% !important;
                display: flex !important;
                justify-content: space-between !important;
            }
            .export-btn {
                flex: 1 !important;
                justify-content: center !important;
            }
            .card-item {
                padding: 14px 12px !important;
            }
            .claim-header {
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 8px !important;
            }
            .evidence-row {
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 6px !important;
            }
            .paper-title {
                white-space: normal !important;
                word-break: break-word !important;
            }
        }

    </style>
</head>
<body>

    <header>
        <a href="/" class="brand">
            <div class="brand-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#C084FC" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z"/>
                    <path d="M10 15.5l-3.5-3.5 1.41-1.41L10 12.67l5.59-5.59L17 8.5l-7 7z" fill="#A855F7"/>
                </svg>
            </div>
            <div class="brand-title">
                LiveTruth Shield
                <span class="brand-badge">LIVE AI</span>
            </div>
        </a>

        <div class="header-meta">
            <div class="model-select-wrap">
                <select id="modelSelector" class="model-dropdown" onchange="onModelChange()" title="Choose Active AI Reasoning Model">
                    <option value="auto">🟣 Auto (Hybrid DeepSeek + Gemini)</option>
                    <option value="groq">⚡ Groq Turbo (GPT-OSS 120B / 20B - 0.6s)</option>
                    <option value="gemini-2.0-flash">🔮 Gemini 2.0 Flash</option>
                    <option value="gemini-1.5-flash">⚡ Gemini 1.5 Flash</option>
                    <option value="deepseek-chat">🚀 DeepSeek-V3</option>
                    <option value="deepseek-reasoner">🔬 DeepSeek-R1 (Deep Reasoner)</option>
                </select>
            </div>
            <div class="status-pill" id="headerStatusPill">
                <span class="status-pulse"></span>
                <span id="headerStatusText">HYBRID: DEEPSEEK + GEMINI</span>
            </div>
            <button class="header-btn" id="btnConfig" onclick="openConfigModal()" title="Configure DeepSeek & Gemini API Keys">
                <span>⚙</span>
                <span>AI Config</span>
            </button>
            <button class="header-btn" id="soundToggle" onclick="toggleSound()">
                <span id="soundIcon">🔊</span>
                <span id="soundLabel">Audio</span>
            </button>
            <button class="autopause-btn active" id="btnAutoPause" onclick="toggleSafetyMode()">
                <span id="apIcon">🟣</span>
                <span id="apText">Safety Mode</span>
            </button>
        </div>
    </header>

    <main>
        <div class="hero">
            <h1>Autonomous Video <span class="gradient-purple">Fact-Checker</span></h1>
            <p>Paste any YouTube URL, video stream, or drop a local video file to perform an exhaustive factual, scientific, and historical veracity audit.</p>

            <div class="quick-chips">
                <span class="chip-label">QUICK AUDITS:</span>
                <button class="demo-chip" onclick="loadSample('Harry Potter and the Philosopher\'s Stone Official Teaser Trailer')">🎬 Harry Potter Trailer</button>
                <button class="demo-chip" onclick="loadSample('https://www.youtube.com/watch?v=mWlmgwV44o')">👤 Avengers: Doomsday</button>
                <button class="demo-chip" onclick="loadSample('https://www.youtube.com/watch?v=P26AE7NLx4Q')">🎙️ Tom Holland Podcast</button>
                <button class="demo-chip" onclick="loadSample('Quantum Computing and Superconductivity Truth')">⚡ Quantum Science</button>
            </div>
        </div>

        <div style="text-align:center;">
            <div class="tabs">
                <button class="tab-btn active" id="tabWeb" onclick="switchMode('web')">🌐 Web URL / Video</button>
                <button class="tab-btn" id="tabLocal" onclick="switchMode('local')">📁 Local MP4 / MKV</button>
            </div>
        </div>

        <!-- URL Input Bar -->
        <div class="input-bar" id="webContainer">
            <input type="text" id="videoUrl" placeholder="Paste YouTube link or enter custom movie/topic title..." autocomplete="off" spellcheck="false" onkeydown="if(event.key==='Enter'){event.preventDefault(); analyzeVideo();}">
            <button id="btnAudit" onclick="analyzeVideo()">
                <span>Audit Truth</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>
        </div>

        <!-- Local File Dropzone -->
        <div class="upload-dropzone" id="localContainer" onclick="document.getElementById('fileInput').click()">
            <input type="file" id="fileInput" accept="video/*,audio/*" style="display:none;" onchange="handleFileSelect(event)">
            <div class="upload-icon">📂</div>
            <p id="uploadText" style="font-weight:600; color:var(--text-main); margin-bottom:4px;">Click or drag & drop MP4, MKV, or WEBM file</p>
            <p style="font-size:12px; color:var(--text-dim);">Automated local audio stream extraction & deep topic fact check</p>
        </div>

        <!-- Results Panel -->
        <div class="panel" id="resultsPanel" style="display:none;">
            <!-- Analytics Overview Banner -->
            <div class="analytics-header">
                <div class="score-block">
                    <div class="score-circle">
                        <svg class="score-svg" viewBox="0 0 70 70">
                            <circle class="score-bg-circle" cx="35" cy="35" r="30"></circle>
                            <circle class="score-val-circle" id="scoreCircleProgress" cx="35" cy="35" r="30"></circle>
                        </svg>
                        <div class="score-number" id="scoreVal">--</div>
                    </div>
                    <div class="score-meta">
                        <h3 id="veracityStatus">Reliability Index</h3>
                        <p id="auditedCount">Audited 0 claims across dialogue</p>
                        <div id="modelBadgeRow" style="display:inline-flex; align-items:center; gap:6px; margin-top:5px; font-family:var(--mono); font-size:11px; color:#60A5FA; background:rgba(59,130,246,0.12); border:1px solid rgba(59,130,246,0.3); border-radius:6px; padding:2px 8px;">
                            <span>🧠</span>
                            <span id="modelBadgeText">Live AI search</span>
                        </div>
                    </div>
                </div>

                <div class="metrics-row">
                    <div class="metric-badge false" id="badgeFalse">❌ 0 False</div>
                    <div class="metric-badge misleading" id="badgeMisleading">⚠️ 0 Misleading</div>
                    <div class="metric-badge verified" id="badgeVerified">✅ 0 Verified</div>
                </div>
            </div>

            <!-- Intel Summary Box -->
            <div class="intel-box" id="intelBox">
                <div class="intel-box-icon">🧠</div>
                <div id="intelText">Fact-check audit complete.</div>
            </div>

            <!-- Political Stance Spectrum Banner (Dashboard) -->
            <div id="politicalSpectrumBox" style="display:none; margin-top:12px; padding:12px 16px; background:rgba(15,23,42,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; font-weight:600; color:#E2E8F0; margin-bottom:6px;">
                    <span style="display:flex; align-items:center; gap:6px;">⚖️ Political Stance Spectrum</span>
                    <span style="font-family:var(--mono); font-size:10px; color:var(--text-dim);">LIVE FACT AUDIT</span>
                </div>
                <div style="position:relative; width:100%; height:6px; background:linear-gradient(90deg, #EF4444 0%, #64748B 50%, #10B981 100%); border-radius:6px; margin:10px 0 6px 0;">
                    <div id="dashSpectrumThumb" style="position:absolute; top:-4px; left:50%; width:14px; height:14px; border-radius:50%; background:#fff; border:2px solid #0F172A; transform:translateX(-50%); transition:left 0.7s cubic-bezier(0.34, 1.56, 0.64, 1); box-shadow:0 0 8px rgba(255,255,255,0.8);"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:10px; font-family:var(--mono); font-weight:500;">
                    <span style="color:#F87171;">🔴 <span id="dashOppName">Opposition</span> <strong id="dashOppPct">0%</strong></span>
                    <span style="color:#94A3B8;">⚪ Neutral <strong id="dashNeutralPct">0%</strong></span>
                    <span style="color:#34D399;">🟢 <span id="dashRulingName">Ruling</span> <strong id="dashRulingPct">0%</strong></span>
                </div>
                <div style="margin-top:6px; display:flex; justify-content:space-between; align-items:center; font-size:11px;">
                    <span id="dashLeanSummary" style="color:#F1F5F9; font-weight:500;">Video Lean: Balanced Political Discourse</span>
                    <span style="color:#60A5FA; font-size:10.5px;">📡 Live Verified: Checked against Daily Fact Feeds</span>
                </div>
            </div>

            <!-- Action Toolbar & Filters -->
            <div class="action-toolbar">
                <div class="filter-group">
                    <button class="filter-btn active" id="fltAll" onclick="filterCards('ALL')">All Claims (<span id="cntAll">0</span>)</button>
                    <button class="filter-btn" id="fltFalse" onclick="filterCards('FALSE')">False (<span id="cntFalse">0</span>)</button>
                    <button class="filter-btn" id="fltMisleading" onclick="filterCards('MISLEADING')">Misleading (<span id="cntMisleading">0</span>)</button>
                    <button class="filter-btn" id="fltVerified" onclick="filterCards('VERIFIED')">Verified (<span id="cntVerified">0</span>)</button>
                </div>

                <div class="share-actions">
                    <button class="export-btn" onclick="copyFactReceipt()">📋 Copy Receipt</button>
                    <button class="export-btn" onclick="exportDossierMarkdown()">📄 Export Dossier</button>
                </div>
            </div>

            <!-- Cards List -->
            <div id="cardsList"></div>

            <!-- Ask Gemini In-Player Assistant -->
            <div class="assistant-section">
                <div class="assistant-header">
                    <div class="assistant-title">
                        <span>💬</span>
                        <span>Ask the Fact Assistant</span>
                        <span class="assistant-badge">Live AI</span>
                    </div>
                </div>
                <div class="assistant-chips">
                    <button class="assistant-chip" onclick="quickAsk('Why was the primary claim marked false or misleading?')">❓ Why was claim flagged?</button>
                    <button class="assistant-chip" onclick="quickAsk('What is the established scientific consensus on this topic?')">🔬 Scientific Consensus</button>
                    <button class="assistant-chip" onclick="quickAsk('Cite the primary peer-reviewed clinical trial or authoritative paper.')">📄 Cite Primary Paper</button>
                    <button class="assistant-chip" onclick="quickAsk('Identify any logical fallacies used in this statement.')">🚩 Explain Fallacies</button>
                </div>
                <div class="assistant-chat" id="assistantChat">
                    <div class="chat-bubble bot">👋 Hi! I am your real-time fact assistant. Ask any question about this video's dialogue, scientific consensus, or primary literature refutations.</div>
                </div>
                <div class="assistant-input-row">
                    <input type="text" id="assistantInput" class="assistant-input" placeholder="Ask about claims, evidence, or study conclusions..." onkeydown="if(event.key==='Enter'){event.preventDefault(); sendAssistantQuestion();}">
                    <button class="assistant-send-btn" onclick="sendAssistantQuestion()">Ask</button>
                </div>
            </div>
        </div>
    </main>

    <div id="lt-toast">Fact-check report copied!</div>




    <script>
        let currentAuditData = null;
        let activeFilter = 'ALL';
        let soundEnabled = true;
        let audioCtxInstance = null;

        function playChime(isPositive = true) {
            if (!soundEnabled) return;
            try {
                if (!audioCtxInstance) {
                    audioCtxInstance = new (window.AudioContext || window.webkitAudioContext)();
                }
                const osc = audioCtxInstance.createOscillator();
                const gain = audioCtxInstance.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(isPositive ? 587.33 : 349.23, audioCtxInstance.currentTime);
                osc.frequency.exponentialRampToValueAtTime(isPositive ? 880.00 : 220.00, audioCtxInstance.currentTime + 0.2);
                gain.gain.setValueAtTime(0.08, audioCtxInstance.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtxInstance.currentTime + 0.25);
                osc.connect(gain);
                gain.connect(audioCtxInstance.destination);
                osc.start();
                osc.stop(audioCtxInstance.currentTime + 0.26);
            } catch (e) {}
        }

        function toggleSound() {
            soundEnabled = !soundEnabled;
            document.getElementById("soundIcon").innerText = soundEnabled ? "🔊" : "🔇";
            document.getElementById("soundToggle").classList.toggle("active", soundEnabled);
            showToast(soundEnabled ? "Audio alerts enabled" : "Audio alerts muted");
        }

        function showToast(msg) {
            const toast = document.getElementById("lt-toast");
            toast.innerText = msg;
            toast.classList.add("show");
            setTimeout(() => toast.classList.remove("show"), 2200);
        }

        function switchMode(mode) {
            const isWeb = mode === 'web';
            document.getElementById('webContainer').style.display = isWeb ? 'flex' : 'none';
            document.getElementById('localContainer').style.display = isWeb ? 'none' : 'block';
            document.getElementById('tabWeb').classList.toggle('active', isWeb);
            document.getElementById('tabLocal').classList.toggle('active', !isWeb);
        }

        function loadSample(query) {
            switchMode('web');
            const input = document.getElementById("videoUrl");
            input.value = query;
            analyzeVideo();
        }

        function renderSkeleton() {
            const panel = document.getElementById("resultsPanel");
            panel.style.display = "block";
            const cardsList = document.getElementById("cardsList");
            cardsList.innerHTML = `
                <div class="skeleton-card">
                    <div class="skeleton-line short"></div>
                    <div class="skeleton-line medium"></div>
                    <div class="skeleton-line"></div>
                </div>
                <div class="skeleton-card">
                    <div class="skeleton-line short"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line medium"></div>
                </div>
            `;
            document.getElementById("scoreVal").innerText = "...";
            document.getElementById("veracityStatus").innerText = "Auditing Claims with Live AI...";
            document.getElementById("auditedCount").innerText = "Cross-referencing scientific authority papers...";
        }

        async function analyzeVideo() {
            const url = document.getElementById("videoUrl").value.trim();
            if (!url) return;

            const btn = document.getElementById("btnAudit");
            btn.innerHTML = `<span>Auditing...</span>`;
            btn.style.opacity = "0.7";
            renderSkeleton();

            try {
                const selModel = document.getElementById("modelSelector") ? document.getElementById("modelSelector").value : "auto";
                const res = await fetch("/api/check?v=" + encodeURIComponent(url) + "&provider=" + encodeURIComponent(selModel));
                const data = await res.json();
                currentAuditData = data;
                renderResults(data);
                playChime((data.score || 0) >= 60);
            } catch (e) {
                alert("Error connecting to server: " + e);
            } finally {
                btn.innerHTML = `<span>Audit Truth</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>`;
                btn.style.opacity = "1";
            }
        }

        async function handleFileSelect(e) {
            const file = e.target.files[0];
            if (!file) return;

            document.getElementById('uploadText').innerText = `Auditing local video: ${file.name}...`;
            renderSkeleton();

            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/check-local', { method: 'POST', body: formData });
                const data = await res.json();
                document.getElementById('uploadText').innerText = `Audited: ${file.name}`;
                currentAuditData = data;
                renderResults(data);
                playChime((data.score || 0) >= 60);
            } catch (err) {
                alert("Failed: " + err);
            }
        }

        function renderResults(data) {
            document.getElementById("resultsPanel").style.display = "block";
            const failed = !!data.error;
            const score = data.score || 0;
            const scoreVal = document.getElementById("scoreVal");
            scoreVal.innerText = failed ? "—" : score + "%";

            // SVG Radial Meter animation (radius 30 => circumference ~188)
            const circle = document.getElementById("scoreCircleProgress");
            const circumference = 188;
            const offset = circumference - (score / 100) * circumference;
            circle.style.strokeDashoffset = offset;

            // Color adaptation
            let strokeColor = "#EF4444";
            let statusTitle = "High Misinformation Risk";
            if (score >= 80) {
                strokeColor = "#10B981";
                statusTitle = "High Empirical Veracity";
            } else if (score >= 60) {
                strokeColor = "#06B6D4";
                statusTitle = "Generally Sound Context";
            } else if (score >= 40) {
                strokeColor = "#F59E0B";
                statusTitle = "Caution: Significant Inaccuracies";
            }

            circle.style.stroke = strokeColor;
            scoreVal.style.color = strokeColor;
            if (failed) { statusTitle = "Audit could not be completed"; strokeColor = "#94A3B8"; circle.style.stroke = strokeColor; scoreVal.style.color = strokeColor; }
            document.getElementById("veracityStatus").innerText = statusTitle;

            const cards = data.cards || [];
            const countFalse = cards.filter(c => c.verdict === 'FALSE').length;
            const countMisleading = cards.filter(c => c.verdict === 'MISLEADING').length;
            const countVerified = cards.filter(c => c.verdict === 'VERIFIED').length;

            document.getElementById("auditedCount").innerText = `Audited ${cards.length} claims across timeline`;
            document.getElementById("badgeFalse").innerText = `❌ ${countFalse} False`;
            document.getElementById("badgeMisleading").innerText = `⚠️ ${countMisleading} Misleading`;
            document.getElementById("badgeVerified").innerText = `✅ ${countVerified} Verified`;
            if (data.model) {
                const mb = document.getElementById("modelBadgeText");
                if (mb) mb.innerText = data.model;
            }

            document.getElementById("cntAll").innerText = cards.length;
            document.getElementById("cntFalse").innerText = countFalse;
            document.getElementById("cntMisleading").innerText = countMisleading;
            document.getElementById("cntVerified").innerText = countVerified;

            if (data.intel) {
                document.getElementById("intelText").innerText = data.intel;
            }

            // Political Spectrum Handling (Dashboard)
            const polBox = document.getElementById("politicalSpectrumBox");
            if (polBox) {
                const pol = data.political_profile;
                if (pol && pol.is_political) {
                    polBox.style.display = "block";
                    const opp = pol.opp_lean_pct || 0;
                    const rul = pol.ruling_lean_pct || 0;
                    const neu = pol.neutral_pct !== undefined ? pol.neutral_pct : Math.max(0, 100 - (opp + rul));
                    const oppEl = document.getElementById("dashOppPct");
                    const neuEl = document.getElementById("dashNeutralPct");
                    const rulEl = document.getElementById("dashRulingPct");
                    const oppNameEl = document.getElementById("dashOppName");
                    const rulNameEl = document.getElementById("dashRulingName");
                    const leanEl = document.getElementById("dashLeanSummary");
                    const thumbEl = document.getElementById("dashSpectrumThumb");
                    if (oppNameEl) oppNameEl.innerText = pol.opp_entity ? pol.opp_entity : "Opposition";
                    if (rulNameEl) rulNameEl.innerText = pol.ruling_entity ? pol.ruling_entity : "Ruling";
                    if (oppEl) oppEl.innerText = opp + "%";
                    if (neuEl) neuEl.innerText = neu + "%";
                    if (rulEl) rulEl.innerText = rul + "%";
                    if (leanEl) leanEl.innerText = "Video Lean: " + (pol.lean_summary || "Political Discourse");
                    let pos = 50 + ((rul - opp) / 2);
                    pos = Math.max(8, Math.min(92, pos));
                    if (thumbEl) thumbEl.style.left = pos + "%";
                } else {
                    polBox.style.display = "none";
                }
            }

            filterCards(activeFilter);
        }

        function filterCards(filter) {
            activeFilter = filter;
            document.getElementById("fltAll").classList.toggle("active", filter === 'ALL');
            document.getElementById("fltFalse").classList.toggle("active", filter === 'FALSE');
            document.getElementById("fltMisleading").classList.toggle("active", filter === 'MISLEADING');
            document.getElementById("fltVerified").classList.toggle("active", filter === 'VERIFIED');

            if (!currentAuditData || !currentAuditData.cards) return;

            const filtered = filter === 'ALL' 
                ? currentAuditData.cards 
                : currentAuditData.cards.filter(c => c.verdict === filter);

            const cardsList = document.getElementById("cardsList");
            if (filtered.length === 0) {
                cardsList.innerHTML = `<div style="text-align:center; padding: 28px; color:var(--text-dim); font-size:13px;">No claims found for this filter.</div>`;
                return;
            }

            cardsList.innerHTML = filtered.map(c => {
                const cClass = c.consensus === 'Universal Consensus' ? 'universal' : (c.consensus === 'Academic Debate' ? 'debate' : 'pseudoscience');
                const cIcon = c.consensus === 'Universal Consensus' ? '🟢' : (c.consensus === 'Academic Debate' ? '🟡' : '🔴');
                const stanceBadge = (c.stance && c.stance !== 'Neutral' && c.stance !== 'None')
                    ? `<span style="font-size:10px; font-weight:600; padding:2px 7px; border-radius:4px; font-family:var(--mono); background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); color:#F1F5F9;">⚖️ ${c.stance}</span>`
                    : '';
                return `
                <div class="card-item ${c.verdict}">
                    <div class="card-header">
                        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                            <span class="verdict-tag ${c.verdict}">
                                ${c.verdict === 'FALSE' ? '❌ FALSE' : (c.verdict === 'MISLEADING' ? '⚠️ MISLEADING' : '✅ VERIFIED')}
                            </span>
                            ${stanceBadge}
                            ${c.fallacy && c.fallacy !== 'None' ? `<span class="fallacy-tag">🚩 ${c.fallacy}</span>` : ''}
                            ${c.consensus && c.consensus !== 'N/A' ? `<span class="consensus-tag ${cClass}">${cIcon} ${c.consensus}</span>` : ''}
                        </div>
                        <span class="timestamp-pill">▶ ${c.timestamp || '00:00'}</span>
                    </div>

                    <div class="quote-box">"${c.quote}"</div>
                    <div class="explanation-text">${c.explanation}</div>

                    <div class="evidence-dossier">
                        <div class="evidence-row" style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <span class="authority-badge">🏛️ Authority: <strong>${c.source}</strong></span>
                            <a href="https://www.google.com/search?q=${encodeURIComponent('\"' + c.source + '\" ' + (c.researchPaper || c.quote))}" target="_blank" rel="noopener" class="authority-link" title="Live official search (resilient against moved or shifted URLs)">🔍 Live Archive Search ↗</a>
                            ${(c.sourceUrl && !c.sourceUrl.includes("google.com")) ? `<a href="${c.sourceUrl}" target="_blank" rel="noopener" class="authority-link" style="opacity:0.85;" title="Direct portal link">🏛️ Direct Portal ↗</a>` : ''}
                        </div>
                        ${c.researchPaper ? `<div class="paper-title">📄 ${c.researchPaper}</div>` : ''}
                        ${c.dataOrigin ? `<div style="font-size:10.5px; color:var(--text-dim); font-family:var(--mono);">Origin: ${c.dataOrigin}</div>` : ''}
                        ${(c.abstractPreview || c.researchSummary) ? `
                        <details class="abstract-accordion">
                            <summary>📄 Study Abstract & Trial Finding</summary>
                            <div class="abstract-content">${c.abstractPreview || c.researchSummary}</div>
                        </details>` : ''}
                    </div>
                </div>
            `}).join("");
        }

        let safetyModeEnabled = true;

        function toggleSafetyMode() {
            safetyModeEnabled = !safetyModeEnabled;
            const btn = document.getElementById("btnAutoPause");
            if (btn) {
                btn.classList.toggle("active", safetyModeEnabled);
                const icon = document.getElementById("apIcon");
                if (icon) icon.innerText = safetyModeEnabled ? "🟣" : "⚪";
                document.getElementById("apText").innerText = safetyModeEnabled ? "Safety Mode" : "Safety Mode: Off";
            }
            showToast(safetyModeEnabled ? "🟣 Safety Mode Active: Auto-Pause on falsehoods" : "Safety Mode Deactivated");
        }

        async function sendAssistantQuestion() {
            const input = document.getElementById("assistantInput");
            const q = input.value.trim();
            if (!q) return;

            input.value = "";
            const chat = document.getElementById("assistantChat");
            chat.innerHTML += `<div class="chat-bubble user">${escapeHtml(q)}</div>`;
            chat.innerHTML += `<div class="chat-bubble bot" id="loadingBubble">Thinking with Live AI...</div>`;
            chat.scrollTop = chat.scrollHeight;

            try {
                const vid = currentAuditData && currentAuditData.video_id ? currentAuditData.video_id : (document.getElementById("videoUrl").value.trim() || "demo");
                const selModel = document.getElementById("modelSelector") ? document.getElementById("modelSelector").value : "auto";
                const res = await fetch("/api/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question: q, video_id: vid, title: document.title, provider: selModel, model: selModel })
                });
                const data = await res.json();
                const lb = document.getElementById("loadingBubble");
                if (lb) lb.remove();

                const answer = data.answer || "No response received.";
                chat.innerHTML += `<div class="chat-bubble bot">${escapeHtml(answer)} <div style="font-size:10px; color:#60A5FA; margin-top:4px; font-family:var(--mono);">⚡ ${data.model || 'AI'}</div></div>`;
            } catch (err) {
                const lb = document.getElementById("loadingBubble");
                if (lb) lb.remove();
                chat.innerHTML += `<div class="chat-bubble bot" style="color:#EF4444;">Error reaching assistant: ${err}</div>`;
            }
            chat.scrollTop = chat.scrollHeight;
        }

        function quickAsk(q) {
            document.getElementById("assistantInput").value = q;
            sendAssistantQuestion();
        }

        function escapeHtml(str) {
            const div = document.createElement("div");
            div.innerText = str;
            return div.innerHTML;
        }

        function copyFactReceipt() {
            if (!currentAuditData) return;
            const score = currentAuditData.score || 0;
            const cards = currentAuditData.cards || [];
            const countFalse = cards.filter(c => c.verdict === 'FALSE').length;
            const countMisleading = cards.filter(c => c.verdict === 'MISLEADING').length;
            const countVerified = cards.filter(c => c.verdict === 'VERIFIED').length;

            let text = `🛡️ LiveTruth Shield // Verification Receipt\n`;
            text += `Score: ${score}% | False: ${countFalse} | Misleading: ${countMisleading} | Verified: ${countVerified}\n\n`;
            cards.slice(0, 4).forEach(c => {
                text += `[${c.verdict}] "${c.quote}" -> Refutation: ${c.explanation} (Source: ${c.source})\n\n`;
            });
            const engineName = (currentAuditData && currentAuditData.model) || "Live AI";
            text += `Audited autonomously by LiveTruth Shield (${engineName} + Search Grounding)`;

            navigator.clipboard.writeText(text).then(() => {
                showToast("📋 Fact-Check Receipt copied to clipboard!");
            });
        }

        function exportDossierMarkdown() {
            if (!currentAuditData) return;
            const engineName = (currentAuditData && currentAuditData.model) || "Live AI";
            let md = `# LiveTruth Shield // Fact-Checking Dossier\n\n`;
            md += `**AI Engine:** ${engineName}\n`;
            md += `**Truth Reliability Score:** ${currentAuditData.score || 0}%\n`;
            md += `**Intel Summary:** ${currentAuditData.intel || 'N/A'}\n\n`;
            md += `## Audited Claims Timeline\n\n`;

            (currentAuditData.cards || []).forEach((c, idx) => {
                md += `### ${idx + 1}. [${c.verdict}] Claim at ${c.timestamp}\n`;
                md += `> "${c.quote}"\n\n`;
                md += `**Factual Analysis:** ${c.explanation}\n\n`;
                md += `- **Primary Authority:** ${c.source} (${c.sourceUrl || '#' })\n`;
                if (c.researchPaper) md += `- **Research Paper:** ${c.researchPaper}\n`;
                if (c.dataOrigin) md += `- **Data Origin:** ${c.dataOrigin}\n`;
                md += `\n---\n\n`;
            });

            const blob = new Blob([md], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `LiveTruth_FactCheck_Dossier.md`;
            a.click();
            URL.revokeObjectURL(url);
            showToast("📄 Dossier downloaded as Markdown!");
        }



    
        // Multi-Model Configuration Functions
        function openConfigModal() {
            document.getElementById('configModal').style.display = 'flex';
            loadAiConfig();
        }

        function closeConfigModal() {
            document.getElementById('configModal').style.display = 'none';
        }

        function togglePasswordVisibility(inputId) {
            const el = document.getElementById(inputId);
            if (el.type === 'password') { el.type = 'text'; } else { el.type = 'password'; }
        }

        async function loadAiConfig() {
            try {
                const res = await fetch('/api/config');
                const data = await res.json();
                if (data) {
                    if (data.provider) document.getElementById('cfgProvider').value = data.provider;
                    if (data.deepseek_model) document.getElementById('cfgDeepseekModel').value = data.deepseek_model;
                    if (data.deepseek_base_url) document.getElementById('cfgDeepseekUrl').value = data.deepseek_base_url;
                    
                    if (data.groq_configured) {
                        const el = document.getElementById('cfgGroqKey');
                        if (el) el.placeholder = `•••••••••••• (${data.groq_masked || 'Saved in .env'})`;
                        const b = document.getElementById('badgeGroqSaved');
                        if (b) { b.style.display = 'inline-flex'; b.innerText = '✅ Saved & Active'; }
                    }
                    if (data.deepseek_configured) {
                        const el = document.getElementById('cfgDeepseekKey');
                        if (el) el.placeholder = `•••••••••••• (${data.deepseek_masked || 'Saved in .env'})`;
                        const b = document.getElementById('badgeDeepseekSaved');
                        if (b) { b.style.display = 'inline-flex'; b.innerText = '✅ Saved & Active'; }
                    }
                    if (data.gemini_configured) {
                        const el = document.getElementById('cfgGeminiKey');
                        if (el) el.placeholder = `•••••••••••• (${data.gemini_masked || 'Saved in .env'})`;
                        const b = document.getElementById('badgeGeminiSaved');
                        if (b) { b.style.display = 'inline-flex'; b.innerText = '✅ Saved & Active'; }
                    }
                    if (data.exa_configured) {
                        const el = document.getElementById('cfgExaKey');
                        if (el) el.placeholder = `•••••••••••• (${data.exa_masked || 'Saved in .env'})`;
                        const b = document.getElementById('badgeExaSaved');
                        if (b) { b.style.display = 'inline-flex'; b.innerText = '✅ Saved & Active'; }
                    }

                    const statusText = document.getElementById('headerStatusText');
                    if (statusText) {
                        const sel = document.getElementById('modelSelector');
                        const isAuto = !sel || sel.value === 'auto';
                        if (isAuto || (data.deepseek_configured && data.gemini_configured)) {
                            statusText.innerText = "HYBRID: DEEPSEEK + GEMINI";
                        } else if (data.groq_configured) {
                            statusText.innerText = "GROQ TURBO ACTIVE";
                        } else if (data.deepseek_configured) {
                            statusText.innerText = "DEEPSEEK ACTIVE";
                        } else if (data.gemini_configured) {
                            statusText.innerText = "GEMINI ACTIVE";
                        } else {
                            statusText.innerText = "HYBRID: DEEPSEEK + GEMINI";
                        }
                    }
                }
            } catch (e) {
                console.warn("Could not load AI config:", e);
            }
        }

        async function saveConfig() {
            const btn = document.getElementById('btnSaveConfig');
            const fb = document.getElementById('cfgFeedback');
            btn.innerText = "Saving & Testing...";
            btn.style.opacity = "0.7";

            const payload = {
                groq_key: document.getElementById('cfgGroqKey') ? document.getElementById('cfgGroqKey').value.trim() : "",
                deepseek_key: document.getElementById('cfgDeepseekKey').value.trim(),
                gemini_key: document.getElementById('cfgGeminiKey').value.trim(),
                provider: document.getElementById('cfgProvider').value,
                deepseek_model: document.getElementById('cfgDeepseekModel').value,
                deepseek_base_url: document.getElementById('cfgDeepseekUrl').value.trim(),
                exa_key: document.getElementById('cfgExaKey') ? document.getElementById('cfgExaKey').value.trim() : ""
            };

            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    fb.style.display = 'block';
                    fb.style.color = '#34D399';
                    fb.innerText = "✅ " + (data.message || "Configuration saved and activated!");
                    showToast("⚡ AI Engine configured successfully!");
                    setTimeout(() => { closeConfigModal(); fb.style.display = 'none'; }, 1200);
                    loadAiConfig();
                } else {
                    fb.style.display = 'block';
                    fb.style.color = '#EF4444';
                    fb.innerText = "❌ Error: " + (data.error || "Could not save configuration");
                }
            } catch (err) {
                fb.style.display = 'block';
                fb.style.color = '#EF4444';
                fb.innerText = "❌ Network Error: " + err;
            } finally {
                btn.innerText = "Save & Activate AI";
                btn.style.opacity = "1";
            }
        }

        function onModelChange() {
            const chosen = document.getElementById('modelSelector').value;
            const statusText = document.getElementById('headerStatusText');
            if (statusText) {
                if (chosen === 'auto') {
                    statusText.innerText = "HYBRID: DEEPSEEK + GEMINI";
                } else if (chosen === 'groq') {
                    statusText.innerText = "GROQ TURBO ACTIVE";
                } else if (chosen.startsWith('gemini')) {
                    statusText.innerText = "GEMINI ACTIVE";
                } else if (chosen.startsWith('deepseek')) {
                    statusText.innerText = "DEEPSEEK ACTIVE";
                }
            }
            showToast("Switched AI model to " + chosen);
        }

        window.addEventListener('DOMContentLoaded', () => {
            loadAiConfig();
        });

    </script>

    <!-- AI Engine Configuration Modal -->
    <div class="modal-overlay" id="configModal" onclick="if(event.target===this) closeConfigModal()">
        <div class="modal-card">
            <div class="modal-header">
                <div class="modal-title">
                    <span>⚡</span>
                    <span>AI Engine & Models Configuration</span>
                </div>
                <button class="modal-close-btn" onclick="closeConfigModal()">✕</button>
            </div>
            <p class="modal-desc" style="background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.25); border-radius:8px; padding:8px 12px; margin-bottom:14px; font-size:11.5px; color:#93C5FD;">🔒 <strong>Keys are permanently saved in <code>backend/.env</code>.</strong> Aapko baar-baar keys enter karne ki zarurat nahi hai. Sirf tabhi type karein jab aapko key change ya update karni ho.</p>

            <div class="config-group">
                <label>
                    <span>⚡ Groq Turbo API Key (0.6s LPU Speed)</span>
                    <span id="badgeGroqSaved" style="display:none; font-size:10px; color:#34D399; font-weight:600; background:rgba(16,185,129,0.12); padding:2px 6px; border-radius:4px; margin-left:8px;">✅ Saved & Active</span>
                    <a href="https://console.groq.com/keys" target="_blank" class="key-link">Get Free Groq Key ↗</a>
                </label>
                <div class="input-with-toggle">
                    <input type="password" id="cfgGroqKey" placeholder="gsk_..." autocomplete="off">
                    <button type="button" class="toggle-pw-btn" onclick="togglePasswordVisibility('cfgGroqKey')">👁️</button>
                </div>
                <div class="field-hint">Ultra-fast LPUs (Llama 3.3 70B & DeepSeek-R1 Distill). Free from GroqCloud.</div>
            </div>

            <div class="config-group">
                <label>
                    <span>🚀 DeepSeek API Key</span>
                    <span id="badgeDeepseekSaved" style="display:none; font-size:10px; color:#34D399; font-weight:600; background:rgba(16,185,129,0.12); padding:2px 6px; border-radius:4px; margin-left:8px;">✅ Saved & Active</span>
                    <a href="https://platform.deepseek.com/" target="_blank" class="key-link">Get DeepSeek Key ↗</a>
                </label>
                <div class="input-with-toggle">
                    <input type="password" id="cfgDeepseekKey" placeholder="sk-..." autocomplete="off">
                    <button type="button" class="toggle-pw-btn" onclick="togglePasswordVisibility('cfgDeepseekKey')">👁️</button>
                </div>
                <div class="field-hint">Supports DeepSeek-V3 & DeepSeek-R1 (Deep Reasoner). Highly accurate empirical fact-checking.</div>
            </div>

            <div class="config-group">
                <label>
                    <span>⚡ Google Gemini API Key</span>
                    <span id="badgeGeminiSaved" style="display:none; font-size:10px; color:#34D399; font-weight:600; background:rgba(16,185,129,0.12); padding:2px 6px; border-radius:4px; margin-left:8px;">✅ Saved & Active</span>
                    <a href="https://aistudio.google.com/apikey" target="_blank" class="key-link">Get Free Gemini Key ↗</a>
                </label>
                <div class="input-with-toggle">
                    <input type="password" id="cfgGeminiKey" placeholder="AIzaSy..." autocomplete="off">
                    <button type="button" class="toggle-pw-btn" onclick="togglePasswordVisibility('cfgGeminiKey')">👁️</button>
                </div>
                <div class="field-hint">Free from Google AI Studio. Powers Gemini 2.0 Flash & Gemini 1.5 Flash.</div>
            </div>

            <div class="config-row">
                <div class="config-group" style="flex:1;">
                    <label>Default Engine Routing</label>
                    <select id="cfgProvider" class="config-select">
                        <option value="auto">Auto Hybrid (DeepSeek + Gemini)</option>
                        <option value="deepseek">DeepSeek Primary</option>
                        <option value="gemini">Google Gemini Primary</option>
                    </select>
                </div>
                <div class="config-group" style="flex:1;">
                    <label>DeepSeek Reasoning Mode</label>
                    <select id="cfgDeepseekModel" class="config-select">
                        <option value="deepseek-chat">DeepSeek-V3 (Fast & Precise)</option>
                        <option value="deepseek-reasoner">DeepSeek-R1 (Deep Reasoner)</option>
                    </select>
                </div>
            </div>

            <div class="config-group">
                <label>DeepSeek Base URL (OpenAI-compatible)</label>
                <input type="text" id="cfgDeepseekUrl" value="https://api.deepseek.com" placeholder="https://api.deepseek.com">
            </div>

            <div class="config-group">
                <label>
                    <span>🌐 Exa AI Neural Search Key (Live Evidence Grounding)</span>
                    <span id="badgeExaSaved" style="display:none; font-size:10px; color:#34D399; font-weight:600; background:rgba(16,185,129,0.12); padding:2px 6px; border-radius:4px; margin-left:8px;">✅ Saved & Active</span>
                    <a href="https://dashboard.exa.ai/api-keys" target="_blank" class="key-link">Exa Dashboard ↗</a>
                </label>
                <div class="input-with-toggle">
                    <input type="password" id="cfgExaKey" placeholder="823f16db-..." autocomplete="off">
                    <button type="button" class="toggle-pw-btn" onclick="togglePasswordVisibility('cfgExaKey')">👁️</button>
                </div>
                <div class="field-hint">Neural web search for 100% active, live evidence citations without dead links.</div>
            </div>

            <div class="modal-actions">
                <button class="modal-btn secondary" onclick="closeConfigModal()">Cancel</button>
                <button class="modal-btn primary" id="btnSaveConfig" onclick="saveConfig()">Save & Activate AI</button>
            </div>
            <div id="cfgFeedback" style="display:none; margin-top:12px; font-size:12px; text-align:center;"></div>
        </div>
    </div>

</body>
</html>
"""


@app.get("/presentation", response_class=HTMLResponse)
def presentation():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "presentation.html"),
        os.path.join(os.path.dirname(__file__), "presentation.html"),
        "presentation.html"
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return HTMLResponse("<h1>Presentation file not found</h1>", status_code=404)


@app.get("/LiveTruth_Shield_Presentation.pptx")
def get_presentation_file():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "LiveTruth_Shield_Presentation.pptx"),
        os.path.join(os.path.dirname(__file__), "LiveTruth_Shield_Presentation.pptx"),
        "LiveTruth_Shield_Presentation.pptx",
        r"C:\Users\Acer\Desktop\LiveTruth_Shield_Presentation.pptx",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "presentation.html"),
        os.path.join(os.path.dirname(__file__), "presentation.html"),
        "presentation.html"
    ]
    for p in candidates:
        if os.path.exists(p):
            return FileResponse(p, filename="LiveTruth_Shield_Presentation.pptx", media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    return Response(status_code=404)


@app.get("/favicon.ico", include_in_schema=False)



def favicon():



    return Response(status_code=204)







@app.get("/api/health")
def health():
    status = ai_engine.get_ai_status()
    return {
        "status": "online",
        "model": status.get("active_display", "Multi-Model AI Engine"),
        "groq_configured": status.get("groq_configured", False),
        "gemini_configured": status.get("gemini_configured", False),
        "deepseek_configured": status.get("deepseek_configured", False),
        "thinking_level": "HIGH",
        "provider": status.get("provider", "groq"),
        "deepseek_model": status.get("deepseek_model", "deepseek-chat"),
        "gemini_models": status.get("gemini_models", [])
    }


@app.get("/api/config")
def get_config():
    return ai_engine.get_ai_status()


@app.post("/api/config")
@app.post("/api/key")
async def save_config_endpoint(data: dict):
    groq_key = data.get("groq_key")
    gemini_key = data.get("gemini_key") or data.get("key")
    deepseek_key = data.get("deepseek_key")
    exa_key = data.get("exa_key")
    provider = data.get("provider")
    deepseek_model = data.get("deepseek_model")
    deepseek_base_url = data.get("deepseek_base_url")

    try:
        new_status = ai_engine.save_ai_config(
            # pyrefly: ignore[unexpected-keyword]
            groq_key=groq_key,
            deepseek_key=deepseek_key,
            gemini_key=gemini_key,
            provider=provider,
            deepseek_model=deepseek_model,
            deepseek_base_url=deepseek_base_url,
            exa_key=exa_key
        )
        return {
            "success": True,
            "message": "AI configuration updated and active!",
            "status": new_status
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_youtube_transcript(video_id: str):
    """Fetch the real caption track. Returns (segments, error). segments = [(seconds, text), ...]."""
    yt = YouTubeTranscriptApi()
    fetched = None
    try:
        fetched = yt.fetch(video_id, languages=["en", "en-US", "en-GB", "en-IN", "hi"])
    except Exception as e1:
        print(f"[!] Preferred-language transcript failed ({e1}). Trying any available track...")
        try:
            fetched = next(iter(yt.list(video_id))).fetch()
        except Exception as e2:
            print(f"[!] No transcript for {video_id}: {e2}")
            return [], str(e2).strip().splitlines()[0] if str(e2).strip() else "no captions"
    try:
        raw = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
    except Exception:
        raw = list(fetched)
    segments = []
    for item in raw:
        if isinstance(item, dict):
            start, text = item.get("start", 0), item.get("text", "")
        else:
            start, text = getattr(item, "start", 0), getattr(item, "text", "")
        text = re.sub(r"\s+", " ", str(text)).strip()
        if text:
            segments.append((int(start), text))
    print(f"[+] Real transcript fetched for {video_id}: {len(segments)} caption segments.")
    return segments, ""


def build_transcript_text(segments, max_chars: int = 14000) -> str:
    """Merge caption fragments into ~12s timestamped lines (whole video, safely under Groq/Gemini TPM budgets)."""
    lines, bucket_start, buf = [], None, []
    for sec, text in segments:
        if bucket_start is None:
            bucket_start = sec
        buf.append(text)
        if sec - bucket_start >= 12:
            lines.append(f"[{bucket_start // 60:02d}:{bucket_start % 60:02d}] {' '.join(buf)}")
            bucket_start, buf = None, []
    if buf:
        lines.append(f"[{bucket_start // 60:02d}:{bucket_start % 60:02d}] {' '.join(buf)}")
    text = "\n".join(lines)
    if len(text) > max_chars:  # very long video: keep evenly spread lines
        stride = -(-len(text) // max_chars)
        text = "\n".join(lines[::stride])
    return text


# ---------------------------------------------------------------------------
# Creator Veracity Index: computed from audits this server actually ran
# ---------------------------------------------------------------------------
CHANNEL_DB_PATH = os.path.join(backend_dir, "channel_history.json")
try:
    with open(CHANNEL_DB_PATH, "r", encoding="utf-8") as _f:
        CHANNEL_DB = json.load(_f)
except Exception:
    CHANNEL_DB = {}


def record_channel_audit(channel: str, video_id: str, title: str, result: dict):
    channel = (channel or "").strip()
    cards = result.get("cards") or []
    if not channel or channel.lower() == "youtube" or not cards:
        return
    count = lambda v: sum(1 for c in cards if c.get("verdict") == v)
    entry = CHANNEL_DB.setdefault(channel, {"channel": channel, "videos": {}})
    entry["videos"][video_id] = {
        "title": title, "score": result.get("score", 0), "claims": len(cards),
        "false": count("FALSE"), "misleading": count("MISLEADING"),
        "verified": count("VERIFIED"), "exaggeration": count("EXAGGERATION"),
        "audited_at": int(time.time()),
    }
    try:
        with open(CHANNEL_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(CHANNEL_DB, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Could not save channel history: {e}")


@app.get("/api/channel-score")
def get_channel_score(channel: str = Query("", description="Channel Name")):
    name = (channel or "").strip()
    videos = (CHANNEL_DB.get(name) or {}).get("videos") or {}
    if not videos:
        return {"channel": name, "veracity_score": None, "total_claims": 0, "videos_audited": 0,
                "rating": "Not enough data yet (audit more of this creator's videos)"}
    total_claims = sum(v["claims"] for v in videos.values())
    score = int(round(sum(v["score"] * v["claims"] for v in videos.values()) / max(1, total_claims)))
    if score >= 80:
        rating = "High Empirical Veracity"
    elif score >= 60:
        rating = "Generally Sound"
    elif score >= 40:
        rating = "Mixed Reliability"
    else:
        rating = "Low Reliability"
    return {"channel": name, "veracity_score": score, "total_claims": total_claims,
            "videos_audited": len(videos), "rating": rating}


def normalize_provider(provider, model):
    """The web dashboard sends a model name in the provider field; split it correctly."""
    p = (provider or "").strip().lower()
    m = (model or "").strip() or None
    if p.startswith("groq") or "groq" in p:
        p = "groq"
    elif p.startswith("deepseek-"):
        m, p = (m or p), "deepseek"
    elif p.startswith("gemini-"):
        m, p = (m or p), "gemini"
    elif p not in ("auto", "groq", "deepseek", "gemini"):
        p = ""
    return (p or None), m


def error_payload(msg: str) -> dict:
    return {
        "score": 0,
        "intel": msg,
        "cards": [],
        "error": msg,
        "model": "none",
        "political_profile": {
            "is_political": False,
            "ruling_lean_pct": 0,
            "opp_lean_pct": 0,
            "neutral_pct": 100,
            "lean_summary": ""
        }
    }


@app.post("/api/ask")
@app.get("/api/ask")
async def ask_assistant(
    q: str = Query("", description="Question asked by viewer"),
    v: str = Query("", description="Video ID or URL"),
    t: str = Query("", description="Timestamp e.g. 02:15"),
    provider: str = Query(None, description="Model provider: auto, deepseek, or gemini"),
    model: str = Query(None, description="Model name e.g. deepseek-chat, deepseek-reasoner"),
    data: dict = None
):
    d = data if isinstance(data, dict) else {}
    question = d.get("question") or q or ""
    video_id = d.get("video_id") or v or ""
    timestamp = d.get("timestamp") or t or "00:00"
    title = d.get("title") or ""
    req_provider, req_model = normalize_provider(d.get("provider") or provider, d.get("model") or model)

    if not question:
        return {"success": False, "error": "No question provided", "answer": "Please type a question."}

    vid, _ = extract_video_id_and_title(video_id, title)
    cached = VERIFICATION_CACHE.get(vid) or VERIFICATION_CACHE.get(video_id) or {}
    intel = cached.get("intel", "")
    cards = cached.get("cards", [])

    try:
        answer_text, used_model = await ai_engine.ask_assistant(
            question=question, video_id=video_id, timestamp=timestamp, title=title,
            cards=cards, intel=intel, provider=req_provider, model=req_model
        )
    except Exception as e:
        msg = f"Assistant unavailable: {e}"
        return {"success": False, "error": msg, "answer": "⚠️ " + msg, "model": "unavailable"}

    return {"success": True, "question": question, "answer": answer_text,
            "timestamp": timestamp, "model": used_model}


@app.post("/api/translate")
async def api_translate(payload: dict):
    """
    Translates text, lists of strings, or full fact-check card arrays
    between English and Hindi using Groq Turbo with Gemini fallback.
    """
    try:
        target_lang = payload.get("target_lang") or "hi"
        cards = payload.get("cards")
        texts = payload.get("texts") or ([payload.get("text")] if payload.get("text") else [])

        if cards and isinstance(cards, list):
            texts_to_trans = []
            for c in cards:
                texts_to_trans.append(c.get("quote", ""))
                texts_to_trans.append(c.get("explanation", "") or c.get("correction", ""))
                texts_to_trans.append(c.get("source", ""))
            
            # Also append summary texts if provided for unified batch translation
            if texts and isinstance(texts, list):
                for t in texts:
                    texts_to_trans.append(str(t))
            
            translated = await ai_engine.translate_content(texts_to_trans, target_lang=target_lang)
            
            translated_cards = []
            idx = 0
            for c in cards:
                card_copy = dict(c)
                if idx < len(translated):
                    card_copy["quote"] = translated[idx]
                    idx += 1
                if idx < len(translated):
                    card_copy["explanation"] = translated[idx]
                    idx += 1
                if idx < len(translated):
                    card_copy["source"] = translated[idx]
                    idx += 1
                translated_cards.append(card_copy)

            translated_texts = []
            while idx < len(translated):
                translated_texts.append(translated[idx])
                idx += 1

            return {"success": True, "cards": translated_cards, "translations": translated_texts, "target_lang": target_lang}

        if texts:
            translated = await ai_engine.translate_content(texts, target_lang=target_lang)
            return {"success": True, "translations": translated, "target_lang": target_lang}

        return {"success": True, "translations": [], "target_lang": target_lang}
    except Exception as e:
        print(f"[!] Translate API error: {e}")
        return {"success": False, "error": str(e), "translations": payload.get("texts") or []}


@app.post("/api/check-local")
async def check_local_file(
    file: UploadFile = File(...),
    provider: str = Query(None),
    model: str = Query(None)
):
    filename = file.filename or "uploaded_video.mp4"
    clean_title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    print(f"[*] Local file '{filename}' (title: '{clean_title}')...")
    return await run_video_audit_pipeline(v=f"file:///{filename}", title=clean_title, channel="", provider=provider, model=model)


async def run_video_audit_pipeline(v: str, title: str = "", channel: str = "",
                                   provider: str = None, model: str = None,
                                   client_captions: list = None):
    video_id, title = extract_video_id_and_title(v, title)
    if not video_id:
        return {"score": 0, "intel": "No active video selected. Play a video or enter a URL above.", "cards": []}

    provider, model = normalize_provider(provider, model)
    status = ai_engine.get_ai_status()
    if not status.get("groq_configured") and not status.get("deepseek_configured") and not status.get("gemini_configured"):
        return error_payload("No AI API key configured. Open the AI Config button (gear) in the dashboard, or put "
                             "GROQ_API_KEY (free from console.groq.com/keys) or GEMINI_API_KEY in backend/.env, then retry.")

    cache_key = f"{video_id}:{provider or 'default'}:{model or ''}"
    if cache_key in VERIFICATION_CACHE and not client_captions:
        print(f"[CACHE HIT] {cache_key}")
        return VERIFICATION_CACHE[cache_key]

    is_topic = video_id.startswith(("local_", "topic_", "ig_")) or v.startswith("file:") or "instagram.com" in v
    segments = []

    # Priority 0: Client-provided browser captions (100% bypasses 403, contains real timestamps)
    if client_captions and isinstance(client_captions, list) and len(client_captions) > 0:
        for c in client_captions:
            if isinstance(c, dict) and c.get("text"):
                try:
                    s_sec = int(c.get("seconds", 0))
                    segments.append((s_sec, str(c.get("text", "")).strip()))
                except (ValueError, TypeError):
                    pass
        if segments:
            print(f"[+] Real-time client captions utilized: {len(segments)} segments for {video_id}.")

    if segments:
        mode = "transcript"
        text_chunk = build_transcript_text(segments)
    elif is_topic:
        mode = "topic"
        if video_id.startswith("ig_") or "instagram.com" in v:
            shortcode = video_id.replace("ig_", "")
            desc = ""
            try:
                client = ai_engine.get_http_client()
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                resp = await client.get(f"https://www.instagram.com/reel/{shortcode}/", headers=headers, timeout=8.0)
                if resp.status_code == 200:
                    og_desc = re.search(r'property="og:description"\s+content="([^"]+)"', resp.text)
                    if og_desc:
                        desc = og_desc.group(1)
            except Exception:
                pass
            text_chunk = f"Title: {title}\nCaption: {desc}".strip()
        else:
            text_chunk = f"Title / topic: {title}"
    else:
        segments = []
        terr = ""
        try:
            segments, terr = await asyncio.to_thread(fetch_youtube_transcript, video_id)
        except Exception as te:
            terr = str(te)

        if segments:
            mode = "transcript"
            text_chunk = build_transcript_text(segments)
        else:
            print(f"[*] Subtitles disabled or unavailable for {video_id} ({terr}). Activating Topic & Claim Audit fallback...")
            mode = "topic"
            clean_title = title if (title and title.lower() not in ["youtube", "live video", ""]) else ""
            if not clean_title:
                try:
                    client = ai_engine.get_http_client()
                    oembed_resp = await client.get(
                        f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
                        timeout=5.0
                    )
                    if oembed_resp.status_code == 200:
                        meta = oembed_resp.json()
                        clean_title = meta.get("title", "")
                        if not channel and meta.get("author_name"):
                            channel = meta.get("author_name")
                except Exception as oe:
                    print(f"[!] oEmbed fallback note: {oe}")
            if clean_title:
                title = clean_title
            text_chunk = f"Video Title / Discussion Subject: {title}\nChannel: {channel or 'YouTube Creator'}\nPlatform: YouTube (Subtitles disabled by uploader)\nPlease analyze and fact-check all key verifiable factual statements, scientific claims, health advice, behavioral rules, and statistics related to this topic."

    try:
        parsed, used_model = await ai_engine.audit_claims(
            text_chunk=text_chunk, title=title, video_id=video_id,
            provider=provider, model=model, mode=mode, segments=segments
        )
    except Exception as err:
        print(f"[Error] Live AI verification failed: {err}")
        return error_payload(f"Live AI verification failed: {err}")

    if not segments and mode == "topic" and not video_id.startswith(("local_", "ig_")):
        parsed["intel"] = f"Audited via Video Topic & Claims Analysis (Subtitles disabled by creator): {parsed.get('intel', '')}"
    print(f"[+] Fact-checked with {used_model}: {len(parsed.get('cards', []))} claims.")
    parsed["video_id"] = video_id
    if parsed.get("cards") and not parsed.get("error"):
        VERIFICATION_CACHE[cache_key] = parsed
        VERIFICATION_CACHE[video_id] = parsed
        while len(VERIFICATION_CACHE) > MAX_CACHE_SIZE * 2:
            VERIFICATION_CACHE.pop(next(iter(VERIFICATION_CACHE)))
        save_cache_to_disk()
    record_channel_audit(channel, video_id, title, parsed)
    return parsed


@app.get("/api/check")
async def check_video_get(
    v: str = Query(..., description="YouTube Video ID or URL"),
    title: str = Query("", description="Page or video title"),
    channel: str = Query("", description="Channel / creator name"),
    provider: str = Query(None, description="Model provider: auto, deepseek, or gemini"),
    model: str = Query(None, description="Specific model name")
):
    return await run_video_audit_pipeline(v=v, title=title, channel=channel, provider=provider, model=model)


@app.post("/api/check")
async def check_video_post(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    v = body.get("v") or body.get("videoId") or ""
    title = body.get("title") or ""
    channel = body.get("channel") or ""
    provider = body.get("provider")
    model = body.get("model")
    client_captions = body.get("captions") or []
    return await run_video_audit_pipeline(v=v, title=title, channel=channel, provider=provider, model=model, client_captions=client_captions)


@app.post("/api/instagram-reel")
async def instagram_reel(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    reel_url = data.get("reelUrl") or data.get("url") or ""
    custom_title = (data.get("title") or "").strip()
    caption = (data.get("caption") or "").strip()
    author = (data.get("author") or "").strip()
    video_src = (data.get("videoSrc") or "").strip()
    audio_track = (data.get("audioTrack") or "").strip()

    # Extract shortcode from Instagram reel URL
    shortcode = data.get("shortcode") or ""
    if not shortcode and ("reel/" in reel_url or "reels/" in reel_url):
        parts = reel_url.split("reel/")[1] if "reel/" in reel_url else reel_url.split("reels/")[1]
        shortcode = parts.split("?")[0].split("/")[0].split("&")[0]

    video_id = f"ig_{shortcode}" if shortcode else ("ig_" + hashlib.md5(reel_url.encode()).hexdigest()[:10])

    # Check cache first (ignore if it contains stale company trivia about Instagram platform)
    if video_id in VERIFICATION_CACHE:
        cached = VERIFICATION_CACHE[video_id]
        cards = cached.get("cards", []) if isinstance(cached, dict) else []
        is_stale_trivia = any("instagram" in str(c.get("quote", "")).lower() and ("kevin systrom" in str(c.get("quote", "")).lower() or "acquired by facebook" in str(c.get("quote", "")).lower() or "launched reels" in str(c.get("quote", "")).lower() or "stories" in str(c.get("quote", "")).lower()) for c in cards)
        if not is_stale_trivia and cards and len(cards) > 0:
            print(f"[CACHE HIT] Instagram Reel {video_id}")
            return cached
        else:
            print(f"[*] Evicted stale trivia cache for {video_id}")
            VERIFICATION_CACHE.pop(video_id, None)

    # Optional speech-to-text if audio transcript can be fetched and caption is brief
    spoken_dialogue = ""
    if transcriber and (video_src or (reel_url and not caption)):
        try:
            target_media = video_src if (video_src and video_src.startswith("http")) else reel_url
            if target_media:
                print(f"[*] Checking speech transcription for Instagram Reel {video_id}...")
                tr_res = await asyncio.wait_for(transcriber.get_transcript(source_url=target_media), timeout=12.0)
                if tr_res and tr_res.get("segments"):
                    segs = tr_res["segments"]
                    spoken_dialogue = " ".join(s[1] for s in segs if len(s) > 1 and s[1])
                    print(f"[+] Transcribed {len(segs)} spoken segments from Instagram Reel.")
        except Exception as te:
            print(f"[!] IG transcription fallback note: {te}")

    # Build structured reel content
    content_blocks = []
    if author:
        content_blocks.append(f"Content Creator / Author: {author}")
    if audio_track:
        content_blocks.append(f"Audio Track: {audio_track}")
    if custom_title and not custom_title.lower().startswith("instagram reel") and custom_title.lower() != "instagram":
        content_blocks.append(f"Post Header: {custom_title}")
    if caption:
        content_blocks.append(f"Reel Caption & On-Screen Assertions:\n{caption}")
    if spoken_dialogue:
        content_blocks.append(f"Spoken Dialogue (Audio Transcript):\n{spoken_dialogue}")

    # If completely empty, NEVER fabricate facts about the company Instagram
    if not caption and not spoken_dialogue and (not custom_title or custom_title.lower() in ["instagram", "instagram reel", ""]):
        return {
            "score": 0,
            "intel": "No readable captions or spoken dialogue could be extracted from this Instagram Reel. Please ensure the reel is playing with sound and click '⚡ Audit Reel Now'.",
            "cards": [],
            "source": "Instagram",
            "video_id": video_id
        }

    reel_content = "\n\n".join(content_blocks)
    audit_title = custom_title or (f"Instagram Reel by {author}" if author else f"Instagram Reel {shortcode}")

    # STRICT GUARD: Caption length < 15 chars AND no spoken dialogue = nothing real to audit
    # This prevents AI from hallucinating Instagram company trivia when reel content is empty
    meaningful_caption = caption.strip() if caption else ""
    meaningful_dialogue = spoken_dialogue.strip() if spoken_dialogue else ""
    if len(meaningful_caption) < 15 and not meaningful_dialogue:
        return {
            "score": 0,
            "intel": f"⚠️ Could not extract sufficient reel content to fact-check. The reel may not have captions or the creator's speech could not be transcribed. Try auditing a reel with visible caption text.",
            "cards": [],
            "source": "Instagram",
            "video_id": video_id
        }

    mode = "transcript" if spoken_dialogue else "topic"

    reel_prompt_text = (
        f"INSTAGRAM REEL AUDIT\n"
        f"Creator / Channel: {author or 'Instagram Creator'}\n"
        f"Reel URL: {reel_url}\n\n"
        f"VERIFIABLE STATEMENTS & CONTENT FROM THIS REEL:\n"
        f"{reel_content}\n\n"
        f"MANDATORY INSTRUCTIONS:\n"
        f"1. You MUST fact-check the actual statements, claims, health/financial/political advice, and facts asserted in this specific reel.\n"
        f"2. Do NOT audit the platform Instagram, Kevin Systrom, or Meta. Audit ONLY the creator's spoken words and caption claims.\n"
        f"3. Return 3 to 6 high-accuracy claim cards with empirical refutations or confirmations."
    )

    try:
        parsed, used_model = await ai_engine.audit_claims(
            text_chunk=reel_prompt_text,
            title=audit_title,
            video_id=video_id,
            mode=mode
        )
    except Exception as err:
        return error_payload(f"Live AI verification failed for Instagram Reel: {err}")

    parsed["source"] = "Instagram"
    parsed["intel"] = f"Instagram Reel ({author or 'Audited Reel'}): {parsed.get('intel', '')}"
    parsed["video_id"] = video_id
    VERIFICATION_CACHE[video_id] = parsed
    save_cache_to_disk()
    return parsed


def free_port_5000():



    try:



        import subprocess



        out = subprocess.check_output("netstat -ano", shell=True, text=True)



        for line in out.splitlines():



            if ":5000" in line and "LISTENING" in line:



                parts = line.strip().split()



                pid = int(parts[-1])



                if pid != os.getpid():



                    print(f"[*] Freeing port 5000: closing old process {pid}...")



                    os.system(f"taskkill /F /PID {pid} >nul 2>&1")



    except Exception:



        pass







if __name__ == "__main__":



    free_port_5000()



    import uvicorn



    



    def auto_open_browser():



        time.sleep(1.2)



        webbrowser.open("http://localhost:5000")







    threading.Thread(target=auto_open_browser, daemon=True).start()







    print("[+] Starting LiveTruth Shield API on http://localhost:5000")



    print("[*] Automatically opening Web Dashboard in browser at http://localhost:5000...")



    uvicorn.run(app, host="0.0.0.0", port=5000)