# 🛡️ LiveTruth Shield — Real-Time Video Fact-Checking Engine & Audit Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Chrome Extension: Manifest V3](https://img.shields.io/badge/Chrome_Extension-Manifest_V3-4285F4.svg?logo=googlechrome&logoColor=white)](https://developer.chrome.com/docs/extensions/mv3/intro/)
[![DeepSeek: V3 & R1](https://img.shields.io/badge/DeepSeek-V3_%26_R1_Reasoner-10B981.svg?logo=deepseek&logoColor=white)](https://platform.deepseek.com/)
[![Google Gemini: 2.5 & 2.0](https://img.shields.io/badge/Google_Gemini-2.5_%26_2.0_Flash-8E75C2.svg?logo=google&logoColor=white)](https://aistudio.google.com/)
[![Tailwind CSS: Dark Theme](https://img.shields.io/badge/Tailwind_CSS-Dark_Theme-38B2AC.svg?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

> **The Problem:** Over 500 hours of video are uploaded online every minute. False health remedies, financial scams, altered historical claims, and sensationalist clickbait spread 6x faster than verified facts. Viewers rarely pause a video to manually cross-reference sources.
>
> **The Solution:** **LiveTruth Shield** is an autonomous, real-time AI fact-checking engine built for YouTube, web video players, and local video files. Powered by a **Hybrid Multi-Model Engine (DeepSeek-V3, DeepSeek-R1 Reasoner, and Google Gemini with Live Search Grounding)**, it scans spoken dialogue across the video timeline, resolves speech-to-text phonetic ambiguities, verifies claims against authoritative global repositories (e.g. Nature, IEEE, NIH, WHO, FAA, CISA), and renders an interactive **Truth Timeline**, **Clickbait Index**, and expandable **Evidence Dossiers**.

---

## ✨ Key Capabilities

### 1. 🔍 Multi-Model AI Engine (DeepSeek + Google Gemini)
- **DeepSeek-R1 & DeepSeek-V3:** Extreme analytical depth, formal logic verification, and chain-of-thought fallacy detection.
- **Google Gemini 2.5 & 2.0 Flash:** Ultra-fast multi-modal reasoning backed by live Google Search grounding.
- **Intelligent Auto-Hybrid Mode:** Automatically routes to the highest-performing active provider with seamless zero-downtime fallback.
- **In-Console Model Switcher:** Switch between DeepSeek-V3, DeepSeek-R1, and Gemini 2.5 Flash on the fly directly in the web dashboard!

### 2. 🎭 Context & Genre Intelligence
- **Intelligent Classification:** Detects whether a video is *Entertainment & Stunts*, *Satire & Parody*, *Science & Tech*, or *News & Politics*.
- **Standardized 4-Verdict Taxonomy:**
  - 🟢 **`VERIFIED`** — Proven by empirical studies or official public records.
  - 🔴 **`FALSE`** — Factually debunked with peer-reviewed or governmental counter-evidence.
  - 🟡 **`MISLEADING`** — Out of context, omitted critical nuances, or manipulated figures.
  - 🟣 **`EXAGGERATION`** — Dramatic hyperbole, comedic exaggeration, or staged stunts (e.g., MrBeast challenge stunts) without penalizing content creators as malicious disinformers.

### 3. 🎯 Clickbait Index & Truth Reliability Bar
- **Clickbait Index:** Computes a sensationalism delta comparing video title/thumbnail promises against actual timeline dialogue (0–100%).
- **Truth Reliability Bar:** Visual gradient progress bar scoring overall factual authenticity.

### 4. ⏱️ Interactive Timeline & Instant Search
- **Color-Coded Timeline Pins:** Jump directly to specific seconds (`00:44`, `04:07`, `19:49`) inside the video player with 1 click.
- **Dynamic Filter Pills:** Filter claims by `All`, `False`, `Verified`, or `Exaggeration`. Selecting a filter dynamically dims inactive timeline pins.
- **Instant Keyword Search:** Real-time claim filtering as you type.

### 5. 🌐 Audited Sources & Deep Research Dossiers
- **Collapsible Source Drawer:** Displays audited institutional domains (Nature, US Dept. of Transportation, IEEE, FAA, CISA) with 1-click external verification links.
- **Evidence Drawer:** Shows exact citation title, empirical consensus findings, and database origins (PubMed Central, NCBI, Cochrane, NREL).

### 6. 🇮🇳 Dual-Language Support & Audio Chimes
- **1-Click Hindi/English Toggle:** Real-time localization of badges, findings, and HUD alerts.
- **Smart Audio Chimes:** Optional soft audio alert (`🔔 Sound` / `🔕 Muted`) when playback hits a debunked claim.
- **1-Click Dossier Export:** Copy full structured markdown audit reports directly to clipboard.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────┐         ┌──────────────────────────────────┐
│   YouTube / Web Video Players   │         │   Local Video Files (MP4 / MKV)  │
│   (Chrome Extension Overlay)    │         │     (Web Console Dashboard)      │
└────────────────┬────────────────┘         └─────────────────┬────────────────┘
                 │ chrome.runtime.sendMessage                 │ HTTP POST /api/check-local
                 ▼                                            ▼
┌─────────────────────────────────┐         ┌──────────────────────────────────┐
│     Background Proxy Worker     │ ──────> │   FastAPI Local AI Server        │
│     (Manifest V3 / 127.0.0.1)   │         │   (http://127.0.0.1:5000)        │
└─────────────────────────────────┘         └─────────────────┬────────────────┘
                                                              │
                     ┌────────────────────────────────────────┴────────────────────────────────────────┐
                     ▼                                                                                 ▼
     ┌────────────────────────────────┐                                                ┌────────────────────────────────┐
     │  YouTube Transcript Extractor  │                                                │  Gemini Multimodal Files API   │
     │  (Timed Dialogue & Captions)   │                                                │  (Audio/Visual Recognition)    │
     └───────────────┬────────────────┘                                                └────────────────┬───────────────┘
                     │                                                                                 │
                     └────────────────────────────────────────┬────────────────────────────────────────┘
                                                              ▼
                                              ┌────────────────────────────────┐
                                              │    Google Gemini 3.8 / 3.1     │
                                              │    + Google Search Grounding   │
                                              └────────────────────────────────┘
                                                              │
                                                              ▼
                                              ┌────────────────────────────────┐
                                              │   JSON Fact-Check Schema       │
                                              │   - Reliability Score & Genre  │
                                              │   - Clickbait Index            │
                                              │   - Audited Citations          │
                                              │   - Standardized Claim Cards   │
                                              └────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+**
- **Google Chrome** (or any Chromium browser like Brave, Edge)
- A **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/apikey)

---

### 2. Backend Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Manjotpreet-Singh/livetruth-shield.git
   cd livetruth-shield/backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your `.env` configuration:
   ```bash
   copy .env.example .env
   ```
   Add your Gemini API key inside `.env`:
   ```env
   GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
   ```
4. Start the server:
   - **Windows:** Double-click `start.bat` (automatically manages port 5000 and launches server).
   - **Terminal:**
     ```bash
     python main.py
     ```
   The backend dashboard will be active at `http://127.0.0.1:5000`.

---

### 3. Chrome Extension Setup
1. Open Chrome and navigate to: `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** (top-left).
4. Select the `livetruth-shield/extension` folder.
5. Open any video on [YouTube](https://www.youtube.com).
6. Click the floating **LiveTruth** pill at the bottom right to open the verification sidebar!

---

### 4. React Dashboard Component
The standalone React (Tailwind CSS) component is located at:
`livetruth-shield/FactCheckAuditDashboard.jsx`

To use it in your React/Vite/Next.js application:
```jsx
import FactCheckAuditDashboard from "./FactCheckAuditDashboard";

export default function App() {
  return (
    <main className="min-h-screen bg-slate-950 p-6 flex justify-center items-center">
      <FactCheckAuditDashboard
        onSeekTimestamp={(seconds) => {
          console.log("Jump video player to second:", seconds);
        }}
      />
    </main>
  );
}
```

---

## 📂 Project Structure

```
livetruth-shield/
├── backend/
│   ├── .env.example             # Environment variable template
│   ├── main.py                  # FastAPI server, Gemini pipeline, & multimodal video auditor
│   ├── requirements.txt         # Python dependencies (fastapi, google-genai, uvicorn, etc.)
│   └── start.bat                # Windows 1-click startup script with port resolution
├── extension/
│   ├── background.js            # Manifest V3 service worker proxy (bypasses CORS/CSP)
│   ├── content.js               # HUD overlay, video playback tracking, filter pills, search
│   ├── manifest.json            # Extension configuration & host permissions
│   ├── popup.html               # Extension popup menu
│   └── sidebar.css              # Dark theme styling, glowing accents & responsive layouts
├── FactCheckAuditDashboard.jsx  # Modular React (Tailwind CSS) Fact-Check component
├── .gitignore                   # Excludes environments, secrets, presentations & cache
└── README.md                    # Project documentation & technical guide
```

---

## 🛡️ Verdict Taxonomy Reference

| Verdict | Color | Criteria | Example |
| :--- | :--- | :--- | :--- |
| **`VERIFIED`** | 🟢 Emerald | Empirically proven by scientific journals, government agencies, or audited data. | Solar roof trickle charging specs validated by NREL. |
| **`FALSE`** | 🔴 Rose | Refuted by concrete contradictory facts or authoritative sources. | Fabricated financial loss figures or fake medical cures. |
| **`MISLEADING`** | 🟡 Amber | Contains partial truths stripped of crucial context or manipulated stats. | Cherry-picked data ignoring primary sample sizes. |
| **`EXAGGERATION`** | 🟣 Purple | Creative, comedic, or staged challenge hyperbole in entertainment videos. | *"I'd save 1,000 hours a year"* in a challenge video. |

---

## 📜 License
Released under the [MIT License](LICENSE). Built for real-time truth and combating automated digital misinformation.
