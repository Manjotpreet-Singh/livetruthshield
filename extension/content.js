(function () {

  let isOpen = false;

  let activeVideoKey = "";

  let lastAnalyzedTitle = "";

  let soundEnabled = true;

  let playedAlerts = new Set();

  let currentCards = [];

  let currentActiveIndex = -1;

  let currentScore = 0;

  let lastTimeUpdate = 0;

  let cachedVideoElement = null;

  let hasAnalyzedCurrentVideo = false;

  let isFetching = false;

  let hudTimer = null;



  let audioCtxInstance = null;
  let autoPauseEnabled = true;
  let triggeredAutoPauseSeconds = new Set();

  function playAlertChime() {

    if (!soundEnabled) return;

    try {

      if (!audioCtxInstance) {

        const AudioCtx = window.AudioContext || window.webkitAudioContext;

        if (!AudioCtx) return;

        audioCtxInstance = new AudioCtx();

      }

      if (audioCtxInstance.state === "suspended") audioCtxInstance.resume();

      const osc = audioCtxInstance.createOscillator();

      const gain = audioCtxInstance.createGain();

      osc.type = "sine";

      osc.frequency.setValueAtTime(587.33, audioCtxInstance.currentTime);

      osc.frequency.exponentialRampToValueAtTime(880, audioCtxInstance.currentTime + 0.16);

      gain.gain.setValueAtTime(0.12, audioCtxInstance.currentTime);

      gain.gain.exponentialRampToValueAtTime(0.01, audioCtxInstance.currentTime + 0.22);

      osc.connect(gain);

      gain.connect(audioCtxInstance.destination);

      osc.start();

      osc.stop(audioCtxInstance.currentTime + 0.22);

    } catch (e) {

      console.warn("Chime failed", e);

    }

  }



  function showToast(msg) {

    let toast = document.getElementById("lt-toast");

    if (!toast) return;

    toast.innerText = msg;

    toast.classList.add("show");

    setTimeout(() => toast.classList.remove("show"), 2400);

  }



  function getActiveVideoElement() {

    if (cachedVideoElement && document.contains(cachedVideoElement)) {

      return cachedVideoElement;

    }

    const videos = document.querySelectorAll("video");

    if (videos.length === 0) return null;

    let chosen = null;

    for (let i = 0; i < videos.length; i++) {

      const v = videos[i];

      if (!v.paused && v.currentTime > 0) {

        chosen = v;

        break;

      }

    }

    if (!chosen && videos.length > 0) chosen = videos[0];

    cachedVideoElement = chosen;

    return chosen;

  }



  function isVideoPlaying() {

    const v = getActiveVideoElement();

    return v && !v.paused && !v.ended && v.currentTime > 0;

  }



  function isWatchPage() {

    if (!window.location.hostname.includes("youtube.com")) return true;

    return window.location.pathname === "/watch";

  }



  function getYouTubeVideoId() {

    if (!window.location.hostname.includes("youtube.com")) return null;

    if (window.location.pathname !== "/watch") return null;

    const params = new URLSearchParams(window.location.search);

    const v = params.get("v");

    return (v && v.length >= 6) ? v : null;

  }



  function getCleanVideoInfo() {

    let title = "";

    let channel = "";



    // 1. Check OpenGraph and Meta tags

    try {

      const ogMeta = document.querySelector('meta[property="og:title"], meta[name="title"]');

      if (ogMeta && ogMeta.content && ogMeta.content.trim()) {

        title = ogMeta.content.trim();

      }

    } catch (e) {}



    // 2. Check YouTube specific DOM headers

    if (!title || title.toLowerCase() === "youtube") {

      try {

        const titleSelectors = [

          "h1.ytd-watch-metadata yt-formatted-string",

          "ytd-watch-metadata #title h1",

          "#above-the-fold #title h1",

          "h1.style-scope.ytd-watch-metadata",

          "#title h1 yt-formatted-string",

          "h1.title",

          "h1"

        ];

        for (const sel of titleSelectors) {

          const el = document.querySelector(sel);

          if (el && el.innerText && el.innerText.trim() && el.innerText.trim().toLowerCase() !== "youtube") {

            title = el.innerText.trim();

            break;

          }

        }

      } catch (e) {}

    }



    // 3. Document title fallback
    if (!title || title.toLowerCase() === "youtube") {
      let t = document.title || "";
      t = t.replace(" - YouTube", "").replace(" | X", "").replace(" • Instagram", "").trim();
      if (t && t.toLowerCase() !== "youtube") {
        title = t;
      }
    }

    // 4. Local video file & direct media URL extraction
    if (!title || title.toLowerCase() === "live video" || window.location.protocol === "file:") {
      try {
        const raw = window.location.pathname || window.location.href || document.title || "";
        const decoded = decodeURIComponent(raw);
        const namePart = decoded.split(/[\\/]/).pop() || "";
        if (namePart && namePart.includes(".")) {
          let clean = namePart.replace(/^(vidssave\.com|y2mate\.is|savefrom\.net|ssyoutube|y2mate|yt1s|snapsave)\s*/i, "");
          clean = clean.replace(/\.(mp4|mkv|mov|webm|avi|flv|m4v|mp3|wav)$/i, "");
          clean = clean.replace(/[\_\.]+/g, " ");
          clean = clean.replace(/\s+/g, " ").trim();
          if (clean && clean.length > 2) {
            title = clean;
          }
        }
      } catch (e) {}
    }

    if (!title) title = "Live Video";



    // 4. Channel extraction

    try {

      const chSelectors = [

        "#channel-name a",

        "ytd-channel-name a",

        "#owner-name a",

        "#upload-info #channel-name",

        ".ytd-video-owner-renderer a",

        "#owner #channel-name"

      ];

      for (const sel of chSelectors) {

        const chEl = document.querySelector(sel);

        if (chEl && chEl.innerText && chEl.innerText.trim()) {

          channel = chEl.innerText.trim();

          break;

        }

      }

    } catch (e) {}



    return { title, channel };

  }



  function getCleanVideoTitle() {

    return getCleanVideoInfo().title;

  }



  function setupExtension() {

    if (document.getElementById("livetruth-btn")) return;

    const video = getActiveVideoElement();

    if (!video && !window.location.hostname.includes("youtube.com")) return;



    // 1. Sleek Floating Action Pill

    const btn = document.createElement("button");

    btn.id = "livetruth-btn";

    btn.innerHTML = `

      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2.2">

        <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z"/>

        <path d="M10 15.5l-3.5-3.5 1.41-1.41L10 12.67l5.59-5.59L17 8.5l-7 7z" fill="#3B82F6"/>

      </svg>

      <span>LiveTruth</span>

      <span class="lt-badge-status" id="lt-pill-status">READY</span>

    `;

    btn.addEventListener("click", togglePanel);

    document.body.appendChild(btn);



    // 2. In-Video Floating Heads-Up Display (HUD Toast)

    if (!document.getElementById("livetruth-video-hud")) {

      const hud = document.createElement("div");

      hud.id = "livetruth-video-hud";

      hud.innerHTML = `

        <span class="lt-hud-badge VERIFIED" id="lt-hud-badge">VERIFIED</span>

        <div class="lt-hud-text">

          <div class="lt-hud-quote" id="lt-hud-quote">Spoken dialogue claim...</div>

          <div class="lt-hud-source" id="lt-hud-source">Authority: <strong>PubMed</strong> • Click for evidence</div>

        </div>

      `;

      hud.addEventListener("click", () => {

        if (!isOpen) togglePanel();

      });

      document.body.appendChild(hud);

    }



    // 3. Minimalist Sidebar Panel

    const panel = document.createElement("div");

    panel.id = "livetruth-panel";

    panel.innerHTML = `

      <div id="lt-toast">✓ Dossier Copied!</div>



      <div class="lt-head">

        <h2>

          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2.2">

            <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z"/>

          </svg>

          LiveTruth

          <span class="lt-badge-status" id="lt-status-badge">Ready</span>

        </h2>

        <div style="display:flex; align-items:center; gap:6px;">

          <button id="lt-export-btn" class="lt-export-btn" title="Export Fact-Check Dossier">📋 Export</button>

          <button id="lt-autopause-btn" class="lt-autopause-toggle active" title="Toggle Auto-Pause on severe falsehoods">🛑 Safety</button>
          <button id="lt-sound-btn" class="lt-sound-toggle active" title="Toggle audio alert">🔔 Sound</button>

          <button id="lt-close" title="Close">✕</button>

        </div>

      </div>



      <!-- Test URL Input Bar -->

      <div class="lt-input-capsule">

        <input type="text" id="lt-manual-url" placeholder="Paste link or test custom URL..." autocomplete="off" spellcheck="false">

        <button id="lt-manual-btn">Test</button>

      </div>



      <!-- Topic Intel -->

      <div id="lt-intel-box">

        <div class="lt-intel-tag" id="lt-intel-tag">Gemini 3.8 High Intel</div>

        <div id="lt-video-title">No Video Active</div>

        <div id="lt-video-summary">Play video or enter URL above to test facts.</div>

      </div>

      <!-- Creator Veracity Index Box -->
      <div id="lt-creator-veracity-box" class="lt-creator-veracity-box" style="display:none; padding:7px 11px; background:rgba(30,58,138,0.25); border:1px solid rgba(59,130,246,0.3); border-radius:8px; margin-bottom:10px; align-items:center; gap:8px;">
        <span style="font-size:14px;">🛡️</span>
        <div style="font-size:11px;">
          <div>Creator Veracity: <strong id="lt-cv-score" style="color:#60A5FA;">--%</strong></div>
          <div id="lt-cv-desc" style="color:var(--lt-text-dim); font-size:10px;">Empirical consistency index</div>
        </div>
      </div>



      <!-- Audited Sources Box -->

      <div id="lt-sources-box" class="lt-sources-box" style="display:none;">

        <button id="lt-sources-toggle" class="lt-sources-toggle" type="button">

          <span style="display:flex; align-items:center; gap:6px;">

            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2">

              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>

              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>

            </svg>

            <span id="lt-sources-count-text">Audited Sources & Citations (0)</span>

          </span>

          <span id="lt-sources-arrow" style="font-size:10px;">▼</span>

        </button>

        <div id="lt-sources-list" class="lt-sources-list closed"></div>

      </div>



      <!-- Reliability Score Bar -->

      <div class="lt-score-box">

        <div class="lt-score-header">

          <span>Truth Reliability</span>

          <strong id="lt-score-val" style="color:#10B981; font-family:var(--lt-mono);">--</strong>

        </div>

        <div class="lt-score-bar-bg">

          <div id="lt-score-bar" class="lt-score-bar"></div>

        </div>

      </div>



      <!-- Timeline Track -->

      <div class="lt-timeline-box">

        <div class="lt-timeline-header">

          <span>Timeline</span>

          <div id="lt-verdict-summary" class="lt-verdict-summary">

            <span style="color:#F87171; font-family:var(--lt-mono); font-size:10px;">0 FALSE</span>

            <span style="color:#34D399; font-family:var(--lt-mono); font-size:10px;">0 VERIFIED</span>

            <span style="color:#FBBF24; font-family:var(--lt-mono); font-size:10px;">0 MISLEADING</span>

          </div>

        </div>

        <div id="lt-timeline-track" class="lt-timeline-track">

          <span style="color:var(--lt-text-dim); font-size:10px;">Waiting for playback...</span>

        </div>

      </div>



      <!-- Claims Feed -->

      <div id="lt-feed" class="lt-cards-feed"></div>

      <!-- Ask Gemini Live Assistant Drawer -->
      <div class="lt-assistant-container">
        <button id="lt-assistant-toggle" class="lt-assistant-toggle" type="button">
          <span style="display:flex; align-items:center; gap:6px;">
            <span>💬</span>
            <span>Ask Gemini Fact Assistant</span>
          </span>
          <span id="lt-assistant-chevron">▼</span>
        </button>
        <div id="lt-assistant-body" class="lt-assistant-body closed">
          <div class="lt-assistant-chips">
            <button class="lt-chip" data-q="Why was this claim flagged as false or misleading?">Why flagged?</button>
            <button class="lt-chip" data-q="What is the scientific consensus on this topic?">Consensus</button>
            <button class="lt-chip" data-q="Cite the primary peer-reviewed clinical trial.">Cite Study</button>
          </div>
          <div id="lt-assistant-chat" class="lt-assistant-chat">
            <div class="lt-chat-msg bot">👋 Ask Gemini anything about claims in this video.</div>
          </div>
          <div class="lt-assistant-input-wrap">
            <input type="text" id="lt-assistant-input" placeholder="Ask Gemini about claims..." autocomplete="off">
            <button id="lt-assistant-send">Ask</button>
          </div>
        </div>
      </div>

    `;

    document.body.appendChild(panel);



    const closeBtn = document.getElementById("lt-close");

    if (closeBtn) closeBtn.addEventListener("click", togglePanel);



    // Auto-Pause Safety Mode Toggle
    const apBtn = document.getElementById("lt-autopause-btn");
    if (apBtn) {
      apBtn.addEventListener("click", () => {
        autoPauseEnabled = !autoPauseEnabled;
        apBtn.classList.toggle("active", autoPauseEnabled);
        showToast(autoPauseEnabled ? "🛑 Safety Mode: ON (Auto-Pause enabled)" : "Safety Mode: OFF");
      });
    }

    // Ask Gemini Assistant Toggle & Handlers
    const asstToggle = document.getElementById("lt-assistant-toggle");
    const asstBody = document.getElementById("lt-assistant-body");
    const asstChevron = document.getElementById("lt-assistant-chevron");
    if (asstToggle && asstBody) {
      asstToggle.addEventListener("click", () => {
        const isClosed = asstBody.classList.contains("closed");
        asstBody.classList.toggle("closed", !isClosed);
        if (asstChevron) asstChevron.innerText = isClosed ? "▲" : "▼";
      });
    }

    const asstInput = document.getElementById("lt-assistant-input");
    const asstSend = document.getElementById("lt-assistant-send");
    const asstChat = document.getElementById("lt-assistant-chat");

    const sendExtensionQuestion = (queryText) => {
      const q = queryText || (asstInput ? asstInput.value.trim() : "");
      if (!q || !asstChat) return;
      if (asstInput) asstInput.value = "";

      const userBubble = document.createElement("div");
      userBubble.className = "lt-chat-msg user";
      userBubble.innerText = q;
      asstChat.appendChild(userBubble);

      const loadingBubble = document.createElement("div");
      loadingBubble.className = "lt-chat-msg bot";
      loadingBubble.innerText = "Thinking with Gemini 3.8 High Reasoning...";
      asstChat.appendChild(loadingBubble);
      asstChat.scrollTop = asstChat.scrollHeight;

      chrome.runtime.sendMessage({
        action: "askQuestion",
        question: q,
        videoId: activeVideoKey,
        title: getCleanVideoTitle()
      }, (resp) => {
        loadingBubble.remove();
        const botBubble = document.createElement("div");
        botBubble.className = "lt-chat-msg bot";
        if (resp && resp.success && resp.data) {
          botBubble.innerHTML = `${resp.data.answer || "No response received."} <div style="font-size:9.5px; color:#60A5FA; margin-top:3px; font-family:var(--lt-mono);">⚡ ${resp.data.model || 'Gemini 3.8 High'}</div>`;
        } else {
          botBubble.innerText = (resp && resp.error) || "Could not reach assistant. Is backend running?";
        }
        asstChat.appendChild(botBubble);
        asstChat.scrollTop = asstChat.scrollHeight;
      });
    };

    if (asstSend) {
      asstSend.addEventListener("click", () => sendExtensionQuestion());
    }
    if (asstInput) {
      asstInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          sendExtensionQuestion();
        }
      });
    }

    // Chips
    document.querySelectorAll(".lt-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        if (asstBody && asstBody.classList.contains("closed")) {
          asstBody.classList.remove("closed");
          if (asstChevron) asstChevron.innerText = "▲";
        }
        sendExtensionQuestion(chip.getAttribute("data-q"));
      });
    });

    const soundBtn = document.getElementById("lt-sound-btn");

    if (soundBtn) {

      soundBtn.addEventListener("click", () => {

        soundEnabled = !soundEnabled;

        soundBtn.innerText = soundEnabled ? "🔔 Sound" : "🔕 Muted";

        soundBtn.classList.toggle("active", soundEnabled);

      });

    }



    const sourcesToggle = document.getElementById("lt-sources-toggle");

    if (sourcesToggle) {

      sourcesToggle.addEventListener("click", () => {

        const list = document.getElementById("lt-sources-list");

        const arrow = document.getElementById("lt-sources-arrow");

        if (list) {

          list.classList.toggle("closed");

          if (arrow) arrow.innerText = list.classList.contains("closed") ? "▼" : "▲";

        }

      });

    }



    const exportBtn = document.getElementById("lt-export-btn");

    if (exportBtn) {

      exportBtn.addEventListener("click", () => {

        if (!currentCards || currentCards.length === 0) {

          showToast("Play video to audit first!");

          return;

        }

        const title = getCleanVideoTitle();

        let report = `# 🛡️ LiveTruth Fact-Checking Dossier\n\n`;

        report += `**Video:** ${title}\n`;

        report += `**Overall Reliability:** ${currentScore || 0}%\n`;

        report += `**Date:** ${new Date().toLocaleDateString()}\n\n`;

        report += `## Verified Claims & Citations\n\n`;

        currentCards.forEach((c, idx) => {

          report += `### ${idx + 1}. [${c.verdict}] ${c.timestamp}\n`;

          report += `> "${c.quote}"\n\n`;

          report += `* **Scientific Finding:** ${c.explanation}\n`;

          report += `* **Primary Authority:** ${c.source}\n`;

          if (c.sourceUrl) report += `* **Verified Source URL:** ${c.sourceUrl}\n`;

          if (c.researchPaper) report += `* **Citation:** ${c.researchPaper}\n`;

          if (c.dataOrigin) report += `* **Data Origin:** ${c.dataOrigin}\n`;

          report += `\n---\n\n`;

        });

        report += `*Audited by LiveTruth Shield (Team HyperSyntax) using Google Gemini 3.8 High Reasoning & Live Search Grounding.*\n`;



        if (navigator.clipboard && navigator.clipboard.writeText) {

          navigator.clipboard.writeText(report).then(() => {

            showToast("✓ Report copied to clipboard!");

          }).catch(() => {

            showToast("✓ Report ready!");

          });

        } else {

          showToast("✓ Report ready!");

        }

      });

    }



    const manualBtn = document.getElementById("lt-manual-btn");

    const manualInput = document.getElementById("lt-manual-url");

    if (manualBtn && manualInput) {

      const runManualTest = () => {

        let val = manualInput.value.trim();

        const currentTitle = getCleanVideoTitle();

        if (!val) {

          val = currentTitle !== "Live Video" ? currentTitle : (getYouTubeVideoId() || window.location.href);

        }

        hasAnalyzedCurrentVideo = true;

        lastAnalyzedTitle = currentTitle;

        fetchUniversalAnalysis(val, val, currentTitle !== "Live Video" ? currentTitle : val);

      };

      manualBtn.addEventListener("click", runManualTest);

      manualInput.addEventListener("keydown", (e) => {

        if (e.key === "Enter") runManualTest();

      });

    }



    panel.addEventListener("click", (e) => {

      const pin = e.target.closest(".lt-timeline-pin");

      if (pin) {

        const seconds = parseInt(pin.getAttribute("data-seconds"), 10);

        const cardId = pin.getAttribute("data-card");

        if (!isNaN(seconds)) seekTo(seconds);

        if (cardId) {

          const targetCard = document.getElementById(cardId);

          if (targetCard) {

            targetCard.scrollIntoView({ behavior: "smooth", block: "center" });

            targetCard.classList.add("active-playback");

            setTimeout(() => targetCard.classList.remove("active-playback"), 1800);

          }

        }

        return;

      }



      const timeBtn = e.target.closest(".lt-time-btn");

      if (timeBtn) {

        const seconds = parseInt(timeBtn.getAttribute("data-seconds"), 10);

        if (!isNaN(seconds)) seekTo(seconds);

        return;

      }



      const researchBtn = e.target.closest(".lt-research-btn");

      if (researchBtn) {

        const targetId = researchBtn.getAttribute("data-target");

        const drawer = document.getElementById(targetId);

        if (drawer) {

          drawer.classList.toggle("open");

          const isDrawerOpen = drawer.classList.contains("open");

          const arrowEl = researchBtn.querySelector(".drawer-arrow");

          if (arrowEl) arrowEl.innerText = isDrawerOpen ? "▲" : "▼";

        }

      }

    });



    renderIdleState();

    attachUniversalVideoSync();

    checkPlaybackStateChange();

  }



  function renderIdleState() {

    const feed = document.getElementById("lt-feed");

    const summaryEl = document.getElementById("lt-video-summary");

    const scoreVal = document.getElementById("lt-score-val");

    const scoreBar = document.getElementById("lt-score-bar");

    const trackEl = document.getElementById("lt-timeline-track");

    const verdictSummary = document.getElementById("lt-verdict-summary");

    const titleEl = document.getElementById("lt-video-title");

    const statusBadge = document.getElementById("lt-status-badge");



    const cleanTitle = customTitle || getCleanVideoTitle();

    if (titleEl) titleEl.innerText = cleanTitle || "Video Ready";

    if (statusBadge) statusBadge.innerText = "Ready";



    if (scoreVal) scoreVal.innerText = "--";

    if (scoreBar) scoreBar.style.width = "0%";

    if (trackEl) trackEl.innerHTML = `<span style="color:var(--lt-text-dim); font-size:10px;">Waiting for playback...</span>`;

    

    if (verdictSummary) {

      verdictSummary.innerHTML = `

        <span style="color:#F87171; font-family:var(--lt-mono); font-size:10px;">0 FALSE</span>

        <span style="color:#34D399; font-family:var(--lt-mono); font-size:10px;">0 VERIFIED</span>

        <span style="color:#FBBF24; font-family:var(--lt-mono); font-size:10px;">0 MISLEADING</span>

      `;

    }

    

    if (summaryEl) summaryEl.innerText = "Video is not playing. Play video or paste URL above to test.";



    if (feed) {

      feed.innerHTML = `

        <div style="text-align:center; padding: 36px 14px; color:var(--lt-text-dim);">

          <div style="color:var(--lt-text-main); font-size:13px; font-weight:500; margin-bottom:5px;">Video Idle</div>

          <div style="font-size:11.5px; line-height:1.45;">Play the video to start real-time fact-checking, or enter any link above and click <strong>Test</strong>.</div>

        </div>

      `;

    }

  }



  function renderEmptyState(msg) {

    const feed = document.getElementById("lt-feed");

    const summaryEl = document.getElementById("lt-video-summary");

    const scoreVal = document.getElementById("lt-score-val");

    const scoreBar = document.getElementById("lt-score-bar");

    const trackEl = document.getElementById("lt-timeline-track");

    const verdictSummary = document.getElementById("lt-verdict-summary");

    const statusBadge = document.getElementById("lt-status-badge");



    if (statusBadge) statusBadge.innerText = "Completed";

    if (scoreVal) scoreVal.innerText = "0%";

    if (scoreBar) scoreBar.style.width = "0%";

    if (trackEl) trackEl.innerHTML = "<span style='color:var(--lt-text-dim); font-size:10px;'>No claims</span>";

    

    if (verdictSummary) {

      verdictSummary.innerHTML = `

        <span style="color:#F87171; font-family:var(--lt-mono); font-size:10px;">0 FALSE</span>

        <span style="color:#34D399; font-family:var(--lt-mono); font-size:10px;">0 VERIFIED</span>

        <span style="color:#FBBF24; font-family:var(--lt-mono); font-size:10px;">0 MISLEADING</span>

      `;

    }



    if (summaryEl) summaryEl.innerText = msg || "No testable factual claims detected.";

    if (feed) {

      feed.innerHTML = `

        <div style="text-align:center; padding: 36px 14px; color:var(--lt-text-dim);">

          <div style="color:var(--lt-text-main); font-size:13px; font-weight:500; margin-bottom:5px;">No Claims Found</div>

          <div style="font-size:11.5px; line-height:1.45;">${msg || "No testable factual claims detected in this video segment."}</div>

        </div>

      `;

    }

  }



  function attachUniversalVideoSync() {

    const video = getActiveVideoElement();

    if (!video || video.hasAttribute("data-lt-sync")) return;

    video.setAttribute("data-lt-sync", "true");



    video.addEventListener("play", () => {

      triggerAnalysisIfPlaying();

    });



    let isTicking = false;

    video.addEventListener("timeupdate", () => {

      if (!hasAnalyzedCurrentVideo && !isFetching && video.currentTime > 0.5 && !video.paused) {

        triggerAnalysisIfPlaying();

      }



      const now = performance.now();

      if (now - lastTimeUpdate < 250) return;

      lastTimeUpdate = now;



      if (!isTicking) {

        window.requestAnimationFrame(() => {

          highlightActiveCard(Math.floor(video.currentTime));

          isTicking = false;

        });

        isTicking = true;

      }

    });

  }



  function triggerAnalysisIfPlaying() {

    const video = getActiveVideoElement();

    if (!video || video.paused) return;



    if (!isWatchPage()) return;

    const ytId = getYouTubeVideoId();

    const url = window.location.href;

    const currentKey = ytId || url;

    const currentInfo = getCleanVideoInfo();



    if (hasAnalyzedCurrentVideo && activeVideoKey === currentKey && lastAnalyzedTitle && lastAnalyzedTitle !== "Live Video") return;



    activeVideoKey = currentKey;

    lastAnalyzedTitle = currentInfo.title;

    hasAnalyzedCurrentVideo = true;

    playedAlerts.clear();

    currentActiveIndex = -1;



    fetchUniversalAnalysis(ytId, url, currentInfo.title);

  }



  function showAutoPauseBanner(card) {
    const existing = document.getElementById("lt-autopause-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.id = "lt-autopause-overlay";
    overlay.innerHTML = `
      <div class="lt-ap-badge">🛑 Safety Mode • Playback Paused</div>
      <div style="font-size:13px; font-weight:700; color:#FFFFFF; margin-bottom:6px;">Critical Misinformation Detected (${card.timestamp})</div>
      <div class="lt-ap-quote">"${card.quote}"</div>
      <div class="lt-ap-refutation"><strong>Empirical Correction:</strong> ${card.explanation}</div>
      <div class="lt-ap-actions">
        <span style="font-size:11px; color:#94A3B8;">🏛️ Source: <strong>${card.source}</strong></span>
        <button id="lt-ap-resume-btn" class="lt-ap-resume-btn">Resume Playback ▶</button>
      </div>
    `;

    document.body.appendChild(overlay);

    const resumeBtn = document.getElementById("lt-ap-resume-btn");
    if (resumeBtn) {
      resumeBtn.addEventListener("click", () => {
        overlay.remove();
        const video = getActiveVideoElement();
        if (video) video.play();
      });
    }
  }

  function highlightActiveCard(currentTime) {

    if (!currentCards.length) return;

    let foundIndex = -1;



    for (let i = 0; i < currentCards.length; i++) {

      const c = currentCards[i];

      if (currentTime >= c.seconds && currentTime <= c.seconds + 6) {

        foundIndex = i;

        break;

      }

    }



    if (foundIndex === currentActiveIndex) return;



    if (currentActiveIndex !== -1) {

      const prevEl = document.getElementById(`card-${currentActiveIndex}`);

      if (prevEl) prevEl.classList.remove("active-playback");

    }



    currentActiveIndex = foundIndex;



    if (foundIndex !== -1) {

      const c = currentCards[foundIndex];

      const activeEl = document.getElementById(`card-${foundIndex}`);

      if (activeEl) {

        activeEl.classList.add("active-playback");

        activeEl.scrollIntoView({ behavior: "smooth", block: "nearest" });



        if ((c.verdict === "FALSE" || c.verdict === "MISLEADING") && !playedAlerts.has(c.seconds)) {

          playedAlerts.add(c.seconds);

          playAlertChime();

          // Auto-Pause Safety Mode
          if (autoPauseEnabled && c.verdict === "FALSE" && !triggeredAutoPauseSeconds.has(c.seconds)) {
            triggeredAutoPauseSeconds.add(c.seconds);
            const video = getActiveVideoElement();
            if (video && !video.paused) {
              video.pause();
              showAutoPauseBanner(c);
            }
          }

        }

      }



      // Update On-Video Floating HUD Toast

      const hud = document.getElementById("livetruth-video-hud");

      if (hud) {

        hud.className = `visible ${c.verdict}`;

        const hBadge = document.getElementById("lt-hud-badge");

        const hQuote = document.getElementById("lt-hud-quote");

        const hSource = document.getElementById("lt-hud-source");

        if (hBadge) {

          hBadge.className = `lt-hud-badge ${c.verdict}`;

          hBadge.innerText = c.verdict;

        }

        if (hQuote) hQuote.innerText = `"${c.quote}"`;

        if (hSource) hSource.innerHTML = `Authority: <strong>${c.source}</strong> • Click for evidence`;



        clearTimeout(hudTimer);

        hudTimer = setTimeout(() => {

          hud.classList.remove("visible");

        }, 6000);

      }

    }

  }



  function togglePanel() {

    isOpen = !isOpen;

    const panel = document.getElementById("livetruth-panel");

    if (panel) panel.classList.toggle("open", isOpen);

  }



  function checkPlaybackStateChange() {

    if (!isWatchPage()) {

      activeVideoKey = "";

      lastAnalyzedTitle = "";

      hasAnalyzedCurrentVideo = false;

      renderIdleState();

      return;

    }



    const ytId = getYouTubeVideoId();

    const url = window.location.href;

    const currentKey = ytId || url;

    const currentInfo = getCleanVideoInfo();



    if (currentKey !== activeVideoKey || (lastAnalyzedTitle === "Live Video" && currentInfo.title !== "Live Video")) {

      activeVideoKey = currentKey;

      lastAnalyzedTitle = currentInfo.title;

      hasAnalyzedCurrentVideo = false;

      playedAlerts.clear();

      currentCards = [];

      currentActiveIndex = -1;



      if (isVideoPlaying()) {

        triggerAnalysisIfPlaying();

      } else {

        renderIdleState();

      }

    }

    attachUniversalVideoSync();

  }



  function seekTo(seconds) {

    const video = getActiveVideoElement();

    if (video) {

      video.currentTime = seconds;

      video.play();

    }

  }



  function fetchUniversalAnalysis(videoId, pageUrl, customTitle) {

    if (isFetching) return;

    isFetching = true;



    const feed = document.getElementById("lt-feed");

    const titleEl = document.getElementById("lt-video-title");

    const summaryEl = document.getElementById("lt-video-summary");

    const statusBadge = document.getElementById("lt-status-badge");



    const cleanTitle = customTitle || getCleanVideoTitle();

    if (titleEl) titleEl.innerText = cleanTitle;

    if (summaryEl) summaryEl.innerText = "Scanning dialogue & grounding claims with Gemini 3.8 High Reasoning...";

    if (statusBadge) statusBadge.innerText = "Auditing...";



    // Shimmer Skeleton Loading

    if (feed) {

      feed.innerHTML = `

        <div style="margin-bottom: 12px; font-size: 11px; color: var(--lt-accent-hover); display: flex; align-items: center; gap: 6px;">

          <span style="display:inline-block; width:6px; height:6px; background:#3B82F6; border-radius:50%;"></span>

          Cross-referencing claims against PubMed, Nature, IEEE & NASA...

        </div>

        <div class="lt-skeleton-card">

          <div class="lt-skeleton-pill"></div>

          <div class="lt-skeleton-line"></div>

          <div class="lt-skeleton-line short"></div>

        </div>

        <div class="lt-skeleton-card">

          <div class="lt-skeleton-pill"></div>

          <div class="lt-skeleton-line"></div>

          <div class="lt-skeleton-line short"></div>

        </div>

        <div class="lt-skeleton-card">

          <div class="lt-skeleton-pill"></div>

          <div class="lt-skeleton-line"></div>

          <div class="lt-skeleton-line short"></div>

        </div>

      `;

    }



    try {

      chrome.runtime.sendMessage({ action: "checkVideo", videoId: (videoId || pageUrl), title: cleanTitle }, (response) => {

        isFetching = false;

        if (chrome.runtime.lastError) {

          renderEmptyState("LiveTruth backend unreachable. Please run start.bat in livetruth-shield/backend.");

          return;

        }

        if (response && response.success && response.data && response.data.cards && response.data.cards.length > 0) {

          renderCards(response.data.cards, response.data.score, response.data.intel, response.data.model);

          // Creator Veracity Index Query
          const channelInfo = getCleanVideoInfo();
          if (channelInfo.channel && channelInfo.channel.toLowerCase() !== "youtube") {
            chrome.runtime.sendMessage({ action: "getChannelScore", channel: channelInfo.channel }, (res) => {
              if (res && res.success && res.data) {
                const cvBox = document.getElementById("lt-creator-veracity-box");
                const cvScore = document.getElementById("lt-cv-score");
                const cvDesc = document.getElementById("lt-cv-desc");
                if (cvBox && cvScore) {
                  cvBox.style.display = "flex";
                  cvScore.innerText = `${res.data.veracity_score}%`;
                  if (cvDesc) {
                    cvDesc.innerText = `${res.data.total_claims} claims audited (${res.data.rating})`;
                  }
                }
              }
            });
          }

        } else if (response && response.success && response.data) {

          renderEmptyState(response.data.intel || "No verifiable claims found for this video.");

        } else if (response && response.error) {

          renderEmptyState(response.error);

        } else {

          renderEmptyState("Backend not running on port 5000. Start backend with start.bat.");

        }

      });

    } catch (err) {

      isFetching = false;

      renderEmptyState("Could not reach backend at localhost:5000. Start backend with start.bat.");

    }

  }



  
  function injectYouTubeScrubberHeatmap(cards) {
    try {
      if (!window.location.hostname.includes("youtube.com")) return;
      const video = getActiveVideoElement();
      if (!video) return;
      const bar = document.querySelector(".ytp-progress-bar, .ytp-progress-bar-container");
      if (!bar) return;

      let layer = document.getElementById("lt-scrubber-heatmap");
      if (!layer) {
        layer = document.createElement("div");
        layer.id = "lt-scrubber-heatmap";
        layer.style.cssText = "position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:45;";
        bar.appendChild(layer);
      }
      layer.innerHTML = "";

      const duration = video.duration || 1;
      cards.forEach((c, idx) => {
        if (!c.seconds && c.seconds !== 0) return;
        const pct = Math.min(100, Math.max(0, (c.seconds / duration) * 100));
        const v = (c.verdict || "VERIFIED").toUpperCase();
        const color = v === "FALSE" ? "#EF4444" : (v === "MISLEADING" ? "#F59E0B" : "#10B981");

        const marker = document.createElement("div");
        marker.className = `lt-scrubber-tick ${v}`;
        marker.style.cssText = `position:absolute; left:${pct}%; top:-3px; width:4px; height:12px; background:${color}; border-radius:2px; pointer-events:auto; cursor:pointer; box-shadow:0 0 6px ${color}; transition:transform 0.15s ease;`;
        marker.title = `[${v}] ${c.timestamp || '00:00'} - ${c.quote}`;

        marker.addEventListener("mouseenter", () => {
          marker.style.transform = "scaleY(1.7) scaleX(1.5)";
        });
        marker.addEventListener("mouseleave", () => {
          marker.style.transform = "scale(1)";
        });
        marker.addEventListener("click", (e) => {
          e.stopPropagation();
          video.currentTime = c.seconds;
          video.play();
          showToast(`▶ Jumped to [${c.timestamp}]: ${c.verdict}`);
          const cardEl = document.getElementById(`card-${idx}`);
          if (cardEl) {
            cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
            cardEl.style.boxShadow = `0 0 16px ${color}`;
            setTimeout(() => { cardEl.style.boxShadow = ""; }, 1800);
          }
        });

        layer.appendChild(marker);
      });
    } catch (e) {
      console.warn("[LiveTruth] Scrubber heatmap error:", e);
    }
  }

  function renderCards(cards, score, intel, modelName) {

    // Sanitize: filter out any bogus cards with quote "N/A" or "System Error"

    const validCards = (cards || []).filter(c => {

      const q = (c.quote || "").trim().toUpperCase();

      const s = (c.source || "").toLowerCase();

      const exp = (c.explanation || "").toLowerCase();

      return q !== "N/A" && q !== "NONE" && q !== "NULL" && q !== "" && !s.includes("system error") && !exp.includes("malformed");

    });



    if (validCards.length === 0) {

      renderEmptyState(intel || "No verifiable claims found in this video.");

      return;

    }



    // Sort cards chronologically across video timeline

    validCards.sort((a, b) => (a.seconds || 0) - (b.seconds || 0));



    score = score || 0;

    currentScore = score;

    currentCards = validCards;

    currentActiveIndex = -1;

    const feed = document.getElementById("lt-feed");

    const scoreVal = document.getElementById("lt-score-val");

    const scoreBar = document.getElementById("lt-score-bar");

    const titleEl = document.getElementById("lt-video-title");

    const summaryEl = document.getElementById("lt-video-summary");

    const trackEl = document.getElementById("lt-timeline-track");

    const verdictSummary = document.getElementById("lt-verdict-summary");

    const statusBadge = document.getElementById("lt-status-badge");



    // Dynamic Video Title & Source Channel

    const videoInfo = getCleanVideoInfo();

    if (titleEl) {

      if (videoInfo.channel && videoInfo.channel.toLowerCase() !== "youtube") {

        titleEl.innerHTML = `<span style="color:#60A5FA; font-weight:600;">${videoInfo.channel}</span> <span style="color:var(--lt-text-dim);">•</span> ${videoInfo.title}`;

      } else {

        titleEl.innerText = videoInfo.title;

      }

      titleEl.title = `${videoInfo.channel ? videoInfo.channel + ' - ' : ''}${videoInfo.title}`;

    }



    // Populate Audited Sources Box

    const sourcesBox = document.getElementById("lt-sources-box");

    const sourcesList = document.getElementById("lt-sources-list");

    const sourcesCountText = document.getElementById("lt-sources-count-text");



    const uniqueSources = [];

    const seen = new Set();

    validCards.forEach(c => {

      const s = (c.source || "").trim();

      if (s && !seen.has(s.toLowerCase())) {

        seen.add(s.toLowerCase());

        uniqueSources.push({

          name: s,

          origin: c.dataOrigin || "Authoritative Database",

          url: c.sourceUrl || `https://www.google.com/search?q=${encodeURIComponent(s + ' ' + (c.researchPaper || c.quote || ''))}`

        });

      }

    });



    if (sourcesBox && sourcesList && uniqueSources.length > 0) {

      sourcesBox.style.display = "block";

      if (sourcesCountText) {

        sourcesCountText.innerText = `Audited Sources & Citations (${uniqueSources.length})`;

      }

      sourcesList.innerHTML = uniqueSources.map(s => `

        <a href="${s.url}" target="_blank" rel="noopener noreferrer" class="lt-source-item" title="Open source: ${s.name}">

          <span>🌐 <strong>${s.name}</strong></span>

          <span class="origin">${s.origin} ↗</span>

        </a>

      `).join("");

    }



    let falseCount = 0, verifiedCount = 0, misleadingCount = 0;

    validCards.forEach(c => {

      const v = (c.verdict || "VERIFIED").toUpperCase();

      if (v === "FALSE") falseCount++;

      else if (v === "VERIFIED" || v === "TRUE") verifiedCount++;

      else misleadingCount++;

    });



    if (statusBadge) statusBadge.innerText = "Audited";
    const intelTag = document.getElementById("lt-intel-tag");
    if (intelTag) {
      intelTag.innerText = modelName ? "⚡ " + modelName : "Gemini 3.8 High Intel";
    }

    if (scoreVal) scoreVal.innerText = `${score}%`;

    if (scoreBar) scoreBar.style.width = `${score}%`;



    if (summaryEl) {

      summaryEl.innerText = intel || "Video claims audited successfully.";

    }



    if (trackEl) {

      trackEl.innerHTML = validCards.map((c, idx) => {

        const v = (c.verdict || "VERIFIED").toUpperCase();

        return `

          <button class="lt-timeline-pin ${v}" data-seconds="${c.seconds}" data-card="card-${idx}" title="${c.timestamp}: ${c.quote}">

            <span>${c.timestamp}</span>

          </button>

        `;

      }).join("");

    }



    if (verdictSummary) {

      verdictSummary.innerHTML = `

        <span style="color:#F87171; font-family:var(--lt-mono); font-size:10px;">${falseCount} FALSE</span>

        <span style="color:#34D399; font-family:var(--lt-mono); font-size:10px;">${verifiedCount} VERIFIED</span>

        <span style="color:#FBBF24; font-family:var(--lt-mono); font-size:10px;">${misleadingCount} MISLEADING</span>

      `;

    }



    if (feed) {

      injectYouTubeScrubberHeatmap(validCards);
      feed.innerHTML = validCards.map((c, idx) => {

        const v = (c.verdict || "VERIFIED").toUpperCase();

        const sourceUrl = c.sourceUrl || `https://www.google.com/search?q=${encodeURIComponent(c.source + ' ' + (c.researchPaper || c.quote || ''))}`;

        return `

          <div id="card-${idx}" class="lt-card ${v}">

            <div class="lt-card-top">

              <div style="display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
                <span class="lt-badge ${v}">${v}</span>
                ${c.fallacy && c.fallacy !== 'None' ? `<span class="lt-fallacy-badge">🚩 ${c.fallacy}</span>` : ''}
                ${c.consensus && c.consensus !== 'N/A' ? `<span class="lt-consensus-badge ${c.consensus === 'Universal Consensus' ? 'universal' : (c.consensus === 'Academic Debate' ? 'debate' : 'pseudoscience')}">${c.consensus === 'Universal Consensus' ? '🟢' : (c.consensus === 'Academic Debate' ? '🟡' : '🔴')} ${c.consensus}</span>` : ''}
              </div>

              <button class="lt-time-btn" data-seconds="${c.seconds}">${c.timestamp}</button>

            </div>

            <div class="lt-quote">"${c.quote}"</div>

            <div class="lt-explanation">${c.explanation}</div>

            <div class="lt-source">Authority: <strong>${c.source}</strong></div>



            <button class="lt-research-btn" data-target="drawer-${idx}">

              <span>Evidence & Source</span>

              <span class="drawer-arrow">▼</span>

            </button>

            

            <div id="drawer-${idx}" class="lt-research-drawer">

              <div style="margin-bottom:4px;"><strong>Citation:</strong> ${c.researchPaper || c.source}</div>

              <div style="margin-bottom:4px;"><strong>Refutation / Finding:</strong> ${c.researchSummary || "Empirical review."}</div>

              <div style="color:#60A5FA; font-size:10.5px; margin-bottom:8px;"><strong>Origin:</strong> ${c.dataOrigin || "Primary Academic Repository"}</div>
              ${(c.abstractPreview || c.researchSummary) ? `
              <details class="lt-abstract-details">
                <summary>📄 Peer-Reviewed Abstract & Findings</summary>
                <div class="lt-abstract-body">${c.abstractPreview || c.researchSummary}</div>
              </details>` : ''}

              <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer" class="lt-source-link-btn" title="Open authoritative external source">

                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">

                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>

                  <polyline points="15 3 21 3 21 9"/>

                  <line x1="10" y1="14" x2="21" y2="3"/>

                </svg>

                <span>Verify Source (${c.source}) ↗</span>

              </a>

            </div>

          </div>

        `;

      }).join("");

    }

  }



  let domCheckTimeout = null;

  const observer = new MutationObserver(() => {

    if (domCheckTimeout) return;

    domCheckTimeout = setTimeout(() => {

      domCheckTimeout = null;

      setupExtension();

      attachUniversalVideoSync();

    }, 400);

  });



  observer.observe(document.body || document.documentElement, { childList: true, subtree: true });



  window.addEventListener("yt-navigate-finish", () => {

    setupExtension();

    checkPlaybackStateChange();

  });

  window.addEventListener("yt-page-data-updated", () => {

    setupExtension();

    checkPlaybackStateChange();

  });

  window.addEventListener("popstate", () => {

    checkPlaybackStateChange();

  });

  window.addEventListener("load", setupExtension);

})();

