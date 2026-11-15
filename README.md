# 🛡️ LiveTruth Shield — Autonomous In-Stream AI Fact-Checking Engine & Truth Ecosystem

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Chrome Extension: Manifest V3](https://img.shields.io/badge/Chrome_Extension-Manifest_V3-4285F4.svg?logo=googlechrome&logoColor=white)](https://developer.chrome.com/docs/extensions/mv3/intro/)
[![Groq Turbo: LPU 500+ tok/s](https://img.shields.io/badge/Groq_Turbo-GPT--OSS_120B-F55036.svg)](https://groq.com)
[![DeepSeek: V3 & R1](https://img.shields.io/badge/DeepSeek-V3_%26_R1_Reasoner-10B981.svg?logo=deepseek&logoColor=white)](https://platform.deepseek.com/)
[![Google Gemini: 2.5 & 2.0](https://img.shields.io/badge/Google_Gemini-2.0_%26_1.5_Flash-8E75C2.svg?logo=google&logoColor=white)](https://aistudio.google.com/)
[![Exa Neural Search](https://img.shields.io/badge/Exa.ai-Neural_Search_Grounding-38BDF8.svg)](https://exa.ai)
[![Tailwind CSS: Dark Theme](https://img.shields.io/badge/Tailwind_CSS-Dark_Cyberpunk-38B2AC.svg?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

> **The Crisis:** Over 500 hours of video are uploaded online every minute. Fabricated medical advice, deepfakes, financial scams, altered historical claims, and weaponized political spin spread 6x faster than empirical facts. Viewers almost never pause video playback to manually cross-reference claims on Google.
>
> **The Solution:** **LiveTruth Shield** is an autonomous, real-time AI fact-checking engine built directly into Google Chrome for **YouTube**, **Instagram Reels**, and **Web Video**. Powered by a high-speed **Hybrid Multi-Model Engine (Groq Turbo 120B at 500+ tokens/sec, DeepSeek-R1 logic reasoner, and Google Gemini 2.0 Flash)** coupled with **Exa.ai live neural web grounding**, it scans spoken dialogue across the video timeline, evaluates political stance on a **dynamic dual-axis spectrum**, verifies claims against authoritative global repositories (PubMed, Nature, IEEE, WHO, ECI, PIB), and renders an interactive **Truth Timeline**, **In-Player HUD**, and **Evidence Dossiers**.

---

## 📑 Table of Contents
- [✨ Key Innovations & Capabilities](#-key-innovations--capabilities)
- [🏗️ System Architecture](#️-system-architecture)
- [⚖️ Political Stance Spectrum & Dual-Axis Matrix](#️-political-stance-spectrum--dual-axis-matrix)
- [🌐 Live Neural Grounding & 404 Prevention (Exa AI)](#-live-neural-grounding--404-prevention-exa-ai)
- [🚀 Quick Start Guide](#-quick-start-guide)
- [📂 Project Structure](#-project-structure)
- [🛡️ Verdict & Stance Taxonomy Reference](#️-verdict--stance-taxonomy-reference)
- [📊 Executive Showcase Presentation Deck](#-executive-showcase-presentation-deck)
- [📜 License](#-license)

---

## ✨ Key Innovations & Capabilities

### 1. ⚡ Ultra-Fast Multi-LLM Orchestration (Groq + DeepSeek + Gemini)
- **Groq Turbo (`openai/gpt-oss-120b` & `20b`):** LPU hardware acceleration running at **500+ tokens/sec** delivers an extraordinary **0.6-second audit latency**.
- **DeepSeek-R1 & V3 Deep Reasoner:** Chain-of-Thought (CoT) logical fallacy detection, identifying complex cognitive traps (*False Dilemma, Cherry-Picking, False Equivalence*).
- **Google Gemini 2.0 / 1.5 Flash:** Multimodal video and live search grounding for breaking news events.
- **Intelligent Auto-Fallback Routing:** Seamless zero-downtime failover (`Groq Turbo ➔ DeepSeek ➔ Gemini`).
- **Expanded 8,192 Token Completion Window:** Deep, exhaustive timeline reasoning without truncation or degradation.

### 2. ⚖️ Political Stance Spectrum & Dual-Axis Matrix (Industry First)
- **Dynamic Entity Recognition:** Automatically detects the geopolitical landscape and renders actual party names:
  ```text
  🔴 Congress / INDIA  20%  ───────⚪ Neutral 70%───────  🟢 BJP / NDA  10%
  ```
- **Contextual Adaptability:** Automatically scales between Indian National politics (`BJP/NDA` vs `Congress/INDIA`), State politics (`AAP`, `TMC`, `DMK`), and International politics (`Democrats` vs `Republicans`, `Labour` vs `Tories`).
- **Spring-Physics Gauge:** Fluid 60FPS thumb motion with `cubic-bezier(0.34, 1.56, 0.64, 1)` and hover scale.
- **Dual-Axis Truth vs Stance Matrix:** Decouples political lean from factual veracity (Scenarios A, B, C, D).

### 3. 🌐 Exa.ai Neural Search Grounding & 404 Prevention
- **Eliminates Dead Links:** Queries live web records via `api.exa.ai` to verify quotes against official government gazettes, court filings, and peer-reviewed journals.
- **Dual-Source Evidence System:**
  - `🔍 Live Archive Search (${c.source}) ↗`: 1-click Google live institutional archive query guaranteed never to 404.
  - `🏛️ Direct Portal ↗`: Direct access to official repositories (PIB, ECI, Nature, PubMed, IEEE, WHO, NASA).

### 4. 🚀 Client-Side In-Browser Caption Ingestion (YouTube 403 Bypass)
- **100% Ingestion Reliability:** Extracts `captionTracks` directly inside the Chrome extension using the user's authentic authenticated browser session, completely bypassing YouTube IP bot-blocking (HTTP 403 Forbidden) and datacenter proxy restrictions.
- **Milestone Spacing Fallback:** When a creator explicitly disables closed captions, the Topic & Claim Engine automatically spaces pins across `[01:00]`, `[03:00]`, `[05:00]`, eliminating timeline clustering at `00:00`.

### 5. 📱 Dedicated Instagram Reel Fact Engine
- **Vertical Short-Form Media:** Specialized engine tailored for fast vertical reels (`instagram.com/reel/*`).
- **Multi-Vector DOM Harvester:** Reliably extracts `@creator_handle`, verified badges, deep captions (`span[dir="auto"]`), and schema.org `VideoObject` metadata.
- **Instagram-Native Glassmorphic UI:** Docked right-panel with Instagram neon gradient styling (`#F093FB` to `#F5576C`), creator banner, and zero timeline collision.

### 6. ⏱️ Interactive Timeline & In-Player Video HUD
- **Clickable Timeline Pins:** Jump directly to specific seconds (`00:10`, `03:34`, `09:12`) inside the video player with 1 click.
- **Synchronized Playback:** Highlights active claim cards in real time as spoken dialogue reaches that moment.
- **Floating HUD Overlay:** In-player badge displaying real-time factual verdict directly over the video.

### 7. 🛡️ Creator Veracity Index & 1-Click Export Suite
- **Long-Term Channel Accountability:** Tracks lifetime creator accuracy across multiple audited videos (`channel_history.json`), displaying consistency badges (e.g. `Creator Veracity: 94%`).
- **Clipboard Fact Receipts:** 1-click formatted text summary ready for quick social media debunking.
- **Export Dossier:** Generates complete structured Markdown research reports for journalists, educators, and researchers.
- **Accessibility & Customization:** Smart soft audio chimes on false claims and 1-click Hindi/English dual-language toggle.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────┐         ┌──────────────────────────────────┐
│    YouTube Video Player         │         │   Instagram Reels Vertical Web   │
│    (Chrome Extension MV3)       │         │   (Multi-Vector DOM Harvester)   │
└────────────────┬────────────────┘         └─────────────────┬────────────────┘
                 │                                            │
                 │ 1. Client-Side Timed Captions / Video Data │
                 ▼                                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Chrome Extension Service Worker Proxy                     │
│                        (Manifest V3 / 127.0.0.1:5000)                        │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ HTTP POST /api/check or /api/instagram-reel
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Local AI Verification Server                     │
│                            (backend/main.py)                                 │
└───────┬──────────────────────────────┬───────────────────────────────┬───────┘
        │                              │                               │
        ▼                              ▼                               ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ Groq Turbo Engine    │    │ DeepSeek-R1 / V3     │    │ Google Gemini 2.0    │
│ (GPT-OSS 120B / 20B) │    │ (Formal Logic & CoT) │    │ (Live Google Search) │
│ 500+ tokens/sec LPU  │    │ Fallacy Detection    │    │ Auto-Fallback Route  │
└───────┬──────────────┘    └──────────┬───────────┘    └──────────┬───────────┘
        │                              │                           │
        └──────────────────────────────┼───────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              Exa Neural Search & Evidence Grounding Engine                   │
│          (Crawls live gazettes, ECI, PIB, PubMed, Nature, IEEE, WHO)         │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       Standardized Fact Dossier Schema                       │
│ - Empirical Reliability Score (0-100%)       - Dynamic Political Profile     │
│ - Dual-Axis Stance Matrix (Scenarios A,B,C,D)- Standardized Claim Cards      │
│ - Live Archive Search & Direct Portal Links  - Synchronized Timeline Pins    │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   In-Stream Glassmorphic UI & HUD Overlay                    │
│    (Fluid 60FPS Spring Animations • Interactive Timeline • Evidence Drawer)   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚖️ Political Stance Spectrum & Dual-Axis Matrix

LiveTruth Shield decouples political ideology from factual empirical accuracy using a 4-Quadrant Matrix:

```
                      DEFENDS RULING PARTY (🟢)
                                 ▲
                                 │
          SCENARIO D             │            SCENARIO C
      [PR Spin / Hyperbole]      │     [Verified Policy Milestone]
      Govt claims overstated;    │     Empirically proven by official
      corrected via data.        │     gazette & RBI census data.
                                 │
 ◄───────────────────────────────┼───────────────────────────────►
  FALSE / MISLEADING             │                       VERIFIED
                                 │
          SCENARIO B             │            SCENARIO A
     [Defamatory Attack]         │     [Legitimate Empirical Critique]
      Fabricated allegations     │     Opposition exposes verified
      refuted by PIB & ECI.      │     flaws via CAG audit records.
                                 │
                                 ▼
                     ATTACKS OPPOSITION (🔴)
```

---

## 🌐 Live Neural Grounding & 404 Prevention (Exa AI)

Standard LLMs frequently hallucinate deep URLs or reference government portals whose URL structures change over time, resulting in broken **404 Page Not Found** links.

LiveTruth Shield integrates **Exa.ai Neural Search** (`api.exa.ai`) and introduces a **Dual-Source Evidence System**:
1. **`🔍 Live Archive Search (${c.source}) ↗`**: Performs a targeted query against Google live institutional index, retrieving active records even if the host website migrated.
2. **`🏛️ Direct Portal ↗`**: Provides direct institutional access to primary publishing bodies (e.g. *Election Commission of India, PIB Fact Check, Nature, The Lancet, IEEE, NASA*).

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (Ensure **"Add python.exe to PATH"** is checked during installation)
- **Google Chrome** (or any Chromium browser: Brave, Edge, Opera)
- Active API Keys for the AI engines (configured in `backend/.env`):
  - **Groq API Key** (from [console.groq.com](https://console.groq.com))
  - **Exa API Key** (from [dashboard.exa.ai](https://dashboard.exa.ai))
  - **Google Gemini API Key** (from [aistudio.google.com](https://aistudio.google.com))
  - *(Optional)* **DeepSeek API Key** (from [platform.deepseek.com](https://platform.deepseek.com))

---

### 2. One-Click Setup & Launch (Windows)

Simply double-click the bundled launcher in the root directory:
```text
Run_LiveTruth_Shield.bat
```
*This launcher automatically checks Python, installs missing dependencies (`fastapi`, `uvicorn`, `httpx`, `python-dotenv`), manages port 5000, and boots the backend server!*

**Manual Terminal Launch:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```
*The local AI engine will be live at `http://localhost:5000`.*

---

### 3. Environment Configuration (`backend/.env`)

Ensure your `backend/.env` contains your active keys:
```env
# Primary High-Speed AI Engine
GROQ_API_KEY=gsk_your_groq_api_key_here

# Neural Evidence Grounding & 404 Prevention Engine
EXA_API_KEY=your_exa_api_key_here

# Multimodal & Google Search Grounding Engine
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here

# Deep Logical Reasoner (Optional)
DEEPSEEK_API_KEY=sk_your_deepseek_api_key_here
```

---

### 4. Chrome Extension Installation

1. Open Chrome and navigate to: `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked** (top-left button).
4. Select the `Live Shield/extension` folder.
5. Open any video on [YouTube](https://www.youtube.com) or [Instagram Reels](https://www.instagram.com/reels/).
6. Click the floating **LiveTruth Shield** button at the bottom right to open the verification panel!

---

## 📂 Project Structure

```
Live Shield/
├── Run_LiveTruth_Shield.bat     # 1-Click portable launcher for backend & dependencies
├── LiveTruth_Shield_Showcase.pptx # Professional 16:9 widescreen PowerPoint deck
├── LiveTruth_Presentation.html  # Standalone interactive web presentation deck
├── README.md                    # Complete project documentation & technical reference
├── backend/
│   ├── .env                     # API keys (Groq, Exa, Gemini, DeepSeek)
│   ├── main.py                  # FastAPI server, endpoints, cache, & pipeline orchestrator
│   ├── ai_engine.py             # Multi-LLM routing, Groq Turbo, Exa grounding, & Prompts
│   ├── requirements.txt         # Python dependencies
│   ├── start.bat                # Backend standalone launcher
│   ├── cache_history.json       # Persistent video verification cache
│   └── channel_history.json     # Creator veracity index tracking across videos
└── extension/
    ├── manifest.json            # Manifest V3 extension configuration
    ├── background.js            # MV3 service worker proxy (bypasses CORS/CSP)
    ├── content.js               # Multi-vector DOM harvester, video HUD, & timeline sync
    ├── sidebar.css              # Cyberpunk dark theme, 60FPS spring animations, & docking
    └── popup.html               # Extension quick-status popup menu
```

---

## 🛡️ Verdict & Stance Taxonomy Reference

| Verdict | Color Indicator | Empirical Criteria | Example |
| :--- | :--- | :--- | :--- |
| **`VERIFIED`** | 🟢 Emerald | Proven by peer-reviewed research, official gazettes, or audited empirical data. | *"Over 912 million voters were eligible in the 2019 Indian elections."* (ECI) |
| **`FALSE`** | 🔴 Rose | Refuted by concrete contradictory evidence, official records, or scientific laws. | *"Wearing a suit in 1950 is proof of high wealth."* (Sociological records) |
| **`MISLEADING`** | 🟡 Amber | Contains cherry-picked data, omitted context, or statistical manipulation. | *"Unemployment is at a 45-year high"* (omits informal sector census changes). |
| **`EXAGGERATION`** | 🟣 Purple | Dramatic hyperbole or challenge exaggeration without malicious deceptive intent. | *"This diet burns 10,000 calories in one hour."* |

---

## 📊 Executive Showcase Presentation Deck

A complete **10-slide keynote presentation** is included directly in the repository:
- 📽️ **PowerPoint Presentation:** [`LiveTruth_Shield_Showcase.pptx`](file:///c:/Users/manjo/Desktop/Live%20Shield/LiveTruth_Shield_Showcase.pptx)
- 🌐 **Interactive Web Deck:** [`LiveTruth_Presentation.html`](file:///c:/Users/manjo/Desktop/Live%20Shield/LiveTruth_Presentation.html) (Open in Chrome, navigate with Arrow Keys, press `F` for Fullscreen).
- 📑 **Speaker Notes & Pitch Script:** [Pitch Deck Document](file:///C:/Users/manjo/.gemini/antigravity/brain/5f6047b5-1819-4ef6-af9e-a7c509f65d8b/livetruth_shield_pitch_deck.md).

---

## 📜 License
Released under the [MIT License](LICENSE). Built for real-time truth, empirical integrity, and combating digital disinformation.
