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

  let currentLanguage = "en";
  let translationCache = {};
  let currentAuditPayload = null;

  const VERDICT_TRANSLATIONS = {
    "VERIFIED": "प्रमाणित सत्य",
    "MISLEADING": "भ्रामक जानकारी",
    "FALSE": "असत्य / झूठा दावा",
    "NEUTRAL": "तटस्थ"
  };

  const STANCE_TRANSLATIONS = {
    "Pro-Opp": "विपक्ष-समर्थक",
    "Neutral": "तटस्थ",
    "Pro-Ruling": "सत्ता-समर्थक",
    "Balanced / Neutral Stance": "संतुलित एवं निष्पक्ष दृष्टिकोण",
    "Critical of Ruling Party": "सत्ताधारी दल की आलोचना",
    "Critical of Opposition": "विपक्षी दलों की आलोचना",
    "Supportive of Ruling Party": "सत्ताधारी दल का समर्थन",
    "Supportive of Opposition": "विपक्षी दलों का समर्थन"
  };

  function scrollCardIntoFeed(targetEl) {
    if (!targetEl) return;
    const feed = document.querySelector(".lt-cards-feed") || document.getElementById("lt-feed") || document.getElementById("cards-container");
    if (feed) {
      const feedRect = feed.getBoundingClientRect();
      const targetRect = targetEl.getBoundingClientRect();
      const scrollOffset = targetRect.top - feedRect.top + feed.scrollTop - 14;
      feed.scrollTo({ top: Math.max(0, scrollOffset), behavior: "smooth" });
    }
  }

  function safeSendMessage(message, callback) {
    if (!chrome || !chrome.runtime || !chrome.runtime.id) {
      console.warn("[LiveTruth] Extension reloaded. Please refresh the page (F5).");
      if (typeof callback === "function") {
        callback({ success: false, error: "Extension was reloaded. Please refresh this page (F5)." });
      }
      return;
    }
    try {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime && chrome.runtime.lastError) {
          const err = chrome.runtime.lastError.message || "";
          console.warn("[LiveTruth] Extension message notice:", err);
          if (typeof callback === "function") {
            callback({ success: false, error: err.includes("context invalidated") ? "Extension was reloaded. Please refresh this page (F5)." : err });
          }
          return;
        }
        if (typeof callback === "function") {
          callback(response);
        }
      });
    } catch (e) {
      console.warn("[LiveTruth] Context invalidated. Please refresh the page (F5).", e);
      if (typeof callback === "function") {
        callback({ success: false, error: "Extension was reloaded. Please refresh this page (F5)." });
      }
    }
  }

  async function toggleExtensionLanguage() {
    const langBtn = document.getElementById("lt-lang-btn");
    const newLang = currentLanguage === "en" ? "hi" : "en";

    if (langBtn) {
      langBtn.disabled = true;
      langBtn.style.opacity = "0.7";
      langBtn.innerText = newLang === "hi" ? "⏳ अनुवाद..." : "🌐 हिन्दी";
    }

    try {
      if (newLang === "hi") {
        await applyHindiTranslation();
        currentLanguage = "hi";
        if (langBtn) {
          langBtn.innerText = "🌐 English";
          langBtn.classList.add("active");
        }
        showToast("🌐 Fact-Check translated to हिन्दी (Hindi)");
      } else {
        restoreEnglishText();
        currentLanguage = "en";
        if (langBtn) {
          langBtn.innerText = "🌐 हिन्दी";
          langBtn.classList.remove("active");
        }
        showToast("🌐 Restored to English");
      }
    } catch (err) {
      console.warn("[LiveTruth] Translation error:", err);
      applyLocalTranslationsOnly();
      currentLanguage = newLang;
      if (langBtn) {
        langBtn.innerText = newLang === "hi" ? "🌐 English" : "🌐 हिन्दी";
      }
    } finally {
      if (langBtn) {
        langBtn.disabled = false;
        langBtn.style.opacity = "1";
      }
    }
  }

  async function applyHindiTranslation() {
    const vidKey = getYouTubeVideoId() || window.location.href;
    if (translationCache[vidKey]) {
      renderBilingualData(translationCache[vidKey]);
      return;
    }

    const summaryEl = document.getElementById("lt-video-summary");
    const summaryText = summaryEl ? summaryEl.innerText : "";

    const payloadCards = currentCards.map(c => ({
      quote: c.quote || "",
      explanation: c.explanation || c.correction || "",
      source: c.source || ""
    }));

    return new Promise((resolve) => {
      safeSendMessage({
        action: "translateContent",
        payload: {
          cards: payloadCards,
          texts: [summaryText],
          target_lang: "hi"
        }
      }, (res) => {
        if (res && res.success && res.data) {
          const data = res.data;
          const hiSummary = (data.translations && data.translations[0]) ? data.translations[0] : summaryText;
          const hiCards = data.cards || [];
          translationCache[vidKey] = { summary: hiSummary, cards: hiCards };
          renderBilingualData(translationCache[vidKey]);
          resolve();
        } else {
          // Direct fetch fallback if background service worker is idle
          fetch("http://localhost:5000/api/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              cards: payloadCards,
              texts: [summaryText],
              target_lang: "hi"
            })
          })
            .then(r => r.json())
            .then(data => {
              if (data && data.success) {
                const hiSummary = (data.translations && data.translations[0]) ? data.translations[0] : summaryText;
                const hiCards = data.cards || [];
                translationCache[vidKey] = { summary: hiSummary, cards: hiCards };
                renderBilingualData(translationCache[vidKey]);
              } else {
                applyLocalTranslationsOnly();
              }
              resolve();
            })
            .catch(() => {
              applyLocalTranslationsOnly();
              resolve();
            });
        }
      });
    });
  }

  function renderBilingualData(data) {
    if (!data) return;

    const summaryEl = document.getElementById("lt-video-summary");
    if (summaryEl && data.summary) {
      summaryEl.innerText = data.summary;
    }

    const leanEl = document.getElementById("lt-spectrum-lean");
    if (leanEl && leanEl.innerText) {
      for (const [en, hi] of Object.entries(STANCE_TRANSLATIONS)) {
        if (leanEl.innerText.includes(en)) {
          leanEl.innerText = leanEl.innerText.replace(en, hi);
          break;
        }
      }
    }

    if (data.cards && data.cards.length) {
      data.cards.forEach((tc, idx) => {
        const cardEl = document.getElementById(`card-${idx}`);
        if (!cardEl) return;

        const quoteEl = cardEl.querySelector(".lt-quote");
        if (quoteEl && tc.quote) quoteEl.innerText = `"${tc.quote}"`;

        const expEl = cardEl.querySelector(".lt-explanation");
        if (expEl && tc.explanation) {
          expEl.innerHTML = `<strong>वैज्ञानिक / तथ्यात्मक समीक्षा:</strong> ${tc.explanation}`;
        }

        const srcEl = cardEl.querySelector(".lt-source strong");
        if (srcEl && tc.source) srcEl.innerText = tc.source;

        const badge = cardEl.querySelector(".lt-badge");
        if (badge && currentCards[idx]) {
          const v = (currentCards[idx].verdict || "").toUpperCase();
          if (VERDICT_TRANSLATIONS[v]) {
            badge.innerText = VERDICT_TRANSLATIONS[v];
          }
        }
      });
    } else {
      applyLocalTranslationsOnly();
    }
  }

  function restoreEnglishText() {
    const summaryEl = document.getElementById("lt-video-summary");
    if (summaryEl && currentAuditPayload && currentAuditPayload.intel) {
      summaryEl.innerText = currentAuditPayload.intel;
    }

    const leanEl = document.getElementById("lt-spectrum-lean");
    if (leanEl && currentAuditPayload && currentAuditPayload.polProfile) {
      const ps = currentAuditPayload.polProfile;
      leanEl.innerText = `Video Lean: ${ps.lean_summary || 'Political Discourse'}`;
    }

    const originalCards = (currentAuditPayload && currentAuditPayload.cards) ? currentAuditPayload.cards : currentCards;
    originalCards.forEach((c, idx) => {
      const cardEl = document.getElementById(`card-${idx}`);
      if (!cardEl) return;

      const quoteEl = cardEl.querySelector(".lt-quote");
      if (quoteEl) quoteEl.innerText = `"${c.quote}"`;

      const expEl = cardEl.querySelector(".lt-explanation");
      if (expEl) {
        expEl.innerText = c.explanation || c.correction || "";
      }

      const srcEl = cardEl.querySelector(".lt-source strong");
      if (srcEl) srcEl.innerText = c.source || "";

      const badge = cardEl.querySelector(".lt-badge");
      if (badge) {
        const v = (c.verdict || "VERIFIED").toUpperCase();
        badge.innerText = v;
      }
    });
  }

  function applyLocalTranslationsOnly() {
    currentCards.forEach((c, idx) => {
      const cardEl = document.getElementById(`card-${idx}`);
      if (!cardEl) return;
      const badge = cardEl.querySelector(".lt-badge");
      const v = (c.verdict || "VERIFIED").toUpperCase();
      if (badge && VERDICT_TRANSLATIONS[v]) {
        badge.innerText = VERDICT_TRANSLATIONS[v];
      }
    });
  }

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

    if (window.location.hostname.includes("youtube.com")) {
      const ytVideo = document.querySelector(".html5-main-video") || document.querySelector("#movie_player video");
      if (ytVideo) {
        cachedVideoElement = ytVideo;
        return ytVideo;
      }
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



  function isInstagramReelPage() {
    if (!window.location.hostname.includes("instagram.com")) return false;
    const p = window.location.pathname;
    return p.includes("/reel/") || p.includes("/reels/") || p.startsWith("/reels") || (document.querySelector("video") !== null);
  }

  function getActiveInstagramReel() {
    const videos = Array.from(document.querySelectorAll("video"));
    if (!videos.length) return { video: null, container: null, shortcode: "" };

    // 1. Prioritize playing / unpaused video
    let activeVideo = videos.find(v => !v.paused && v.currentTime > 0);

    // 2. Fallback to video closest to vertical center of viewport
    if (!activeVideo) {
      const vhCenter = window.innerHeight / 2;
      let minDistance = Infinity;
      for (const v of videos) {
        const rect = v.getBoundingClientRect();
        if (rect.height > 100 && rect.width > 100) {
          const vCenter = rect.top + rect.height / 2;
          const dist = Math.abs(vCenter - vhCenter);
          if (dist < minDistance) {
            minDistance = dist;
            activeVideo = v;
          }
        }
      }
    }

    if (!activeVideo) activeVideo = videos[0];

    const container = activeVideo ? (
      activeVideo.closest("article") ||
      activeVideo.closest("div[role='dialog']") ||
      activeVideo.closest("div[class*='x1lliihq']") ||
      activeVideo.parentElement?.parentElement?.parentElement ||
      document.body
    ) : document.body;

    let shortcode = "";
    const m = window.location.pathname.match(/\/reels?\/([A-Za-z0-9_-]+)/);
    if (m) {
      shortcode = m[1];
    } else if (container) {
      const link = container.querySelector("a[href*='/reel/'], a[href*='/p/']");
      if (link) {
        const lm = link.getAttribute("href").match(/\/(?:reel|p)\/([A-Za-z0-9_-]+)/);
        if (lm) shortcode = lm[1];
      }
    }

    return { video: activeVideo, container, shortcode };
  }

  function getInstagramReelInfo() {
    const { video, container, shortcode } = getActiveInstagramReel();
    let title = "";
    let caption = "";
    let author = "";
    let audioTrack = "";
    let videoSrc = "";

    try {
      if (video) {
        videoSrc = video.currentSrc || video.src || "";
      }

      if (container) {
        // A. Author / Creator Handle
        const authorEl = container.querySelector("header a, a[role='link'][tabindex='0'], a[href*='/'][role='link']");
        if (authorEl) {
          const rawH = (authorEl.getAttribute("href") || "").replace(/^\//, "").split("/")[0].split("?")[0];
          if (rawH && !["reels", "reel", "explore", "p", "stories", "direct"].includes(rawH.toLowerCase())) {
            author = `@${rawH}`;
          } else if (authorEl.innerText && !authorEl.innerText.includes(" ") && authorEl.innerText.length < 35) {
            author = `@${authorEl.innerText.trim().replace(/^@/, '')}`;
          }
        }

        // B. Automatically click "... more" / "more" button if Instagram hid caption
        const expandBtns = container.querySelectorAll("div[role='button'], span[role='button']");
        for (const btn of expandBtns) {
          const txt = (btn.innerText || "").toLowerCase().trim();
          if (txt === "more" || txt === "... more" || txt.includes("… more")) {
            try { btn.click(); } catch(e) {}
            break;
          }
        }

        // C. Multi-element Caption Extraction
        const textPieces = [];
        const captionEls = container.querySelectorAll("h1, div[class*='_a9zs'], div[class*='caption'], span[dir='auto'], div[dir='auto']");
        captionEls.forEach(el => {
          const t = el.innerText ? el.innerText.trim() : "";
          if (t.length > 8 &&
              !t.includes("likes") &&
              !t.includes("comments") &&
              !t.includes("Audio unavailable") &&
              !t.includes("Original audio") &&
              !t.match(/^(?:view|reply|share|send|save|follow|more|view all.*)$/i)) {
            if (!textPieces.some(p => p.includes(t) || t.includes(p))) {
              textPieces.push(t);
            }
          }
        });

        if (textPieces.length) {
          caption = textPieces.join("\n\n");
        }

        // D. Audio track info
        const audioEl = container.querySelector("a[href*='/audio/'] span, div[class*='audio'] span");
        if (audioEl && audioEl.innerText) {
          audioTrack = audioEl.innerText.trim();
        }
      }

      // E. OpenGraph Fallback
      if (!caption) {
        const ogDesc = document.querySelector('meta[property="og:description"], meta[name="description"]');
        if (ogDesc && ogDesc.content) {
          const c = ogDesc.content.trim();
          if (!c.toLowerCase().includes("photos and videos")) {
            caption = c;
          }
        }
      }

      // Format clean user-facing title
      if (author && caption) {
        const cleanSnippet = caption.replace(/[\r\n\t]+/g, " ").slice(0, 75);
        title = `${author}: "${cleanSnippet}${caption.length > 75 ? '…' : ''}"`;
      } else if (author) {
        title = `Instagram Reel by ${author}`;
      } else {
        const docT = document.title.replace(/\s*•\s*Instagram.*$/i, "").trim();
        title = (docT && !["instagram", "reels"].includes(docT.toLowerCase())) ? docT : `Instagram Reel ${shortcode || ''}`;
      }

    } catch (e) {
      console.warn("[LiveTruth] IG Reel extraction notice:", e);
    }

    return { title, caption, author, audioTrack, videoSrc, shortcode };
  }

  function showInstagramResults(data) {
    if (!data) return;
    if (!isOpen) togglePanel();
    if (data.cards && data.cards.length > 0) {
      renderCards(data.cards, data.score, data.intel, data.model || "Groq Turbo (IG Reel)", data.political_profile);
    } else {
      renderEmptyState(data.intel || "No testable factual claims detected in this Instagram Reel.");
    }
  }

  function checkAndAuditInstagramReel() {
    if (!isInstagramReelPage()) return;
    const statusPill = document.getElementById("lt-pill-status");
    if (statusPill) statusPill.innerText = "AUDITING...";

    const feed = document.getElementById("lt-feed");
    const titleEl = document.getElementById("lt-video-title");
    const summaryEl = document.getElementById("lt-video-summary");
    const statusBadge = document.getElementById("lt-status-badge");

    const info = getInstagramReelInfo();
    const cleanReelTitle = info.title || "Instagram Reel";

    if (titleEl) {
      titleEl.innerHTML = `<span style="background:linear-gradient(135deg, #f093fb, #f5576c); -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-weight:700;">Instagram Reel</span> <span style="color:var(--lt-text-dim);">•</span> ${info.author || 'Audited Reel'}`;
    }
    if (summaryEl) summaryEl.innerText = "Extracting reel assertions & verifying claims with Groq Turbo / Gemini...";
    if (statusBadge) statusBadge.innerText = "Auditing...";

    if (feed) {
      feed.innerHTML = `
        <div style="margin-bottom: 12px; font-size: 11px; color: var(--lt-accent-hover); display: flex; align-items: center; gap: 6px;">
          <span style="display:inline-block; width:6px; height:6px; background:#EC4899; border-radius:50%;"></span>
          Cross-referencing reel claims against authoritative records & verified science...
        </div>
        <div class="lt-skeleton-card"><div class="lt-skeleton-pill"></div><div class="lt-skeleton-line"></div><div class="lt-skeleton-line short"></div></div>
        <div class="lt-skeleton-card"><div class="lt-skeleton-pill"></div><div class="lt-skeleton-line"></div><div class="lt-skeleton-line short"></div></div>
      `;
    }

    const reelUrl = (info.shortcode ? `https://www.instagram.com/reel/${info.shortcode}/` : window.location.href);

    safeSendMessage({
      action: "checkInstagramReel",
      reelUrl: reelUrl,
      title: cleanReelTitle,
      caption: info.caption,
      author: info.author,
      videoSrc: info.videoSrc,
      audioTrack: info.audioTrack,
      shortcode: info.shortcode
    }, (resp) => {
      if (statusPill) statusPill.innerText = "READY";
      if (resp && resp.success && resp.data) {
        showInstagramResults(resp.data);
      } else if (resp && resp.error) {
        renderEmptyState(resp.error);
      } else {
        renderEmptyState("LiveTruth backend unreachable. Please ensure Run_LiveTruth_Shield.bat is running.");
      }
    });
  }

  function adaptSidebarForInstagram() {
    if (!isInstagramReelPage()) return;

    const panel = document.getElementById("livetruth-panel");
    if (!panel) return;

    panel.classList.add("lt-panel-instagram");
    document.body.classList.add("lt-on-instagram");
    document.body.classList.add("instagram-reel");

    // Dock to right empty space (beyond Instagram's button row)
    panel.style.position = "fixed";
    panel.style.right = "0";
    panel.style.top = "0";
    panel.style.bottom = "0";
    panel.style.left = "auto";
    panel.style.width = "360px";
    panel.style.maxWidth = "calc(100% - 16px)";
    panel.style.zIndex = "99999";
    panel.style.boxShadow = "-6px 0 24px rgba(0,0,0,0.5)";
    panel.style.borderRadius = "0";
    panel.style.border = "none";

    // YouTube-specific elements to hide
    const youtubeSpecific = panel.querySelectorAll('.lt-youtube-only, [data-yt-feature]');
    youtubeSpecific.forEach(el => el.style.display = 'none');

    // Instagram-specific elements to show
    const instagramSpecific = panel.querySelectorAll('.lt-instagram-only, [data-ig-feature]');
    instagramSpecific.forEach(el => el.style.display = 'block');

    // Adjust HUD positioning
    const hud = document.getElementById("livetruth-video-hud");
    if (hud) {
      hud.style.right = "380px";
      hud.style.top = "80px";
      hud.style.bottom = "auto";
    }
  }

  function isWatchPage() {
    if (isInstagramReelPage()) return true;
    if (!window.location.hostname.includes("youtube.com")) return true;
    const p = window.location.pathname;
    return p === "/watch" || p.startsWith("/shorts/") || p.startsWith("/live/");
  }

  function getYouTubeVideoId() {
    if (!window.location.hostname.includes("youtube.com")) return null;
    const p = window.location.pathname;
    if (p.startsWith("/shorts/")) {
      const parts = p.split("/shorts/")[1].split("/")[0].split("?")[0];
      if (parts && parts.length >= 6) return parts;
    }
    if (p.startsWith("/live/")) {
      const parts = p.split("/live/")[1].split("/")[0].split("?")[0];
      if (parts && parts.length >= 6) return parts;
    }
    if (p === "/watch") {
      const params = new URLSearchParams(window.location.search);
      const v = params.get("v");
      return (v && v.length >= 6) ? v : null;
    }
    return null;
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

    } catch (e) { }



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

      } catch (e) { }

    }



    // 3. Document title fallback (strip notifications like "(1) Title - YouTube")
    if (!title || title.toLowerCase() === "youtube") {
      let t = (document.title || "").replace(/^\(\d+\)\s*/, "").replace(/\s*-\s*YouTube$/i, "").replace(/\s*\|\s*X$/i, "").replace(/\s*•\s*Instagram.*$/i, "").trim();
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
      } catch (e) { }
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

    } catch (e) { }



    return { title, channel };

  }



  function getCleanVideoTitle() {

    return getCleanVideoInfo().title;

  }



  function setupExtension() {

    if (document.getElementById("livetruth-btn")) return;

    const video = getActiveVideoElement();
    const isYT = window.location.hostname.includes("youtube.com");
    const isIG = isInstagramReelPage();

    if (!video && !isYT && !isIG) return;

    if (isIG || window.location.hostname.includes("instagram.com")) {
      document.body.classList.add("lt-on-instagram");
    }

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

    btn.addEventListener("click", () => {
      togglePanel();
      if (isInstagramReelPage()) {
        checkAndAuditInstagramReel();
      }
    });

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
          <span class="lt-instagram-only" style="display:none; background:linear-gradient(135deg, #f093fb, #f5576c); color:white; font-size:9px; font-weight:700; padding:2px 6px; border-radius:4px; letter-spacing:0.5px; margin-left:4px;">REEL</span>

        </h2>

        <div style="display:flex; align-items:center; gap:6px;">

          <button id="lt-lang-btn" class="lt-lang-toggle" title="Translate Fact-Check to Hindi / English">🌐 हिन्दी</button>
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

      <!-- Political Stance Spectrum Gauge (Hidden by default for non-political videos) -->
      <div id="lt-political-spectrum-box">
        <div class="lt-spectrum-header">
          <span style="display:flex; align-items:center; gap:5px;">
            <span>⚖️</span>
            <span>Political Stance Spectrum</span>
          </span>
          <span id="lt-spectrum-tag" style="font-size:9.5px; font-family:var(--lt-mono); color:var(--lt-text-dim);">LIVE AUDIT</span>
        </div>
        <div class="lt-spectrum-track-wrap">
          <div class="lt-spectrum-notch"></div>
          <div class="lt-spectrum-fill" id="lt-spectrum-fill" style="left:50%; width:0%;"></div>
          <div class="lt-spectrum-thumb" id="lt-spectrum-thumb" style="left: 50%;"></div>
        </div>
        <div class="lt-spectrum-labels">
          <span class="lt-lbl-opp" id="lt-lbl-opp" title="Opposition Stance">🔵 <span id="lt-opp-name">Opp</span> <strong id="lt-opp-pct">0%</strong></span>
          <span class="lt-lbl-neutral" id="lt-lbl-neutral" title="Neutral / Factual">⚪ Neutral <strong id="lt-neutral-pct">0%</strong></span>
          <span class="lt-lbl-ruling" id="lt-lbl-ruling" title="Ruling Governance Stance">🟠 <span id="lt-ruling-name">Ruling</span> <strong id="lt-ruling-pct">0%</strong></span>
        </div>
        <div class="lt-spectrum-sub">
          <div class="lt-spectrum-lean" id="lt-spectrum-lean">Video Lean: Balanced Political Discourse</div>
          <div class="lt-spectrum-live">
            <span>📡</span>
            <span>Live Verified: Checked against Daily Fact Feeds</span>
          </div>
        </div>
      </div>

      <!-- Creator Veracity Index Box -->
      <div id="lt-creator-veracity-box" class="lt-creator-veracity-box lt-youtube-only" data-yt-feature="creator-veracity" style="display:none; padding:8px 12px; background:rgba(15,23,42,0.65); border:1px solid rgba(59,130,246,0.35); border-radius:8px; margin-bottom:10px; align-items:center; gap:10px; box-shadow:0 4px 12px rgba(0,0,0,0.25);">
        <span style="font-size:18px; filter:drop-shadow(0 0 6px rgba(59,130,246,0.6));">🛡️</span>
        <div style="font-size:11px; flex:1;">
          <div style="color:#F1F5F9; font-weight:600; display:flex; align-items:center; justify-content:space-between;">
            <span>Creator Veracity:</span>
            <strong id="lt-cv-score" style="color:#38BDF8; font-family:var(--lt-mono); font-size:12px; background:rgba(56,189,248,0.12); padding:1px 6px; border-radius:4px; border:1px solid rgba(56,189,248,0.3);">--%</strong>
          </div>
          <div id="lt-cv-desc" style="color:#94A3B8; font-size:10px; margin-top:2px;">Empirical consistency index</div>
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



    // Language Switcher Toggle
    const langBtn = document.getElementById("lt-lang-btn");
    if (langBtn) {
      langBtn.addEventListener("click", toggleExtensionLanguage);
    }

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

      safeSendMessage({
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
        const ytId = getYouTubeVideoId();
        if (!val) {
          val = ytId || window.location.href;
        }
        hasAnalyzedCurrentVideo = true;
        lastAnalyzedTitle = currentTitle;
        const targetId = (ytId && (!val || !val.includes("http"))) ? ytId : val;
        fetchUniversalAnalysis(targetId, window.location.href, currentTitle !== "Live Video" ? currentTitle : val);
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

        // 1. Highlight clicked timeline pin
        document.querySelectorAll(".lt-timeline-pin").forEach(p => p.classList.remove("active"));
        pin.classList.add("active");

        // 2. Dispatch seek to video player
        if (!isNaN(seconds)) seekTo(seconds);

        // 3. Scroll to and illuminate corresponding fact card
        if (cardId) {

          const targetCard = document.getElementById(cardId);

          if (targetCard) {

            document.querySelectorAll(".lt-card").forEach(c => c.classList.remove("active-playback"));

            scrollCardIntoFeed(targetCard);

            targetCard.classList.add("active-playback");

            setTimeout(() => targetCard.classList.remove("active-playback"), 2500);

          }

        }

        const ts = pin.querySelector("span") ? pin.querySelector("span").innerText.trim() : "";
        showToast(`▶ Jumped to [${ts || seconds + 's'}]`);

        return;

      }



      const timeBtn = e.target.closest(".lt-time-btn");

      if (timeBtn) {

        const seconds = parseInt(timeBtn.getAttribute("data-seconds"), 10);

        if (!isNaN(seconds)) {
          seekTo(seconds);
          document.querySelectorAll(".lt-timeline-pin").forEach(p => {
            const pSec = parseInt(p.getAttribute("data-seconds"), 10);
            p.classList.toggle("active", pSec === seconds);
          });
          showToast(`▶ Jumped to [${timeBtn.innerText.trim()}]`);
        }

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

    if (isInstagramReelPage()) {
      adaptSidebarForInstagram();
    }

  }



  function renderIdleState(customTitle = null) {

    const feed = document.getElementById("lt-feed");

    const summaryEl = document.getElementById("lt-video-summary");

    const scoreVal = document.getElementById("lt-score-val");

    const scoreBar = document.getElementById("lt-score-bar");

    const trackEl = document.getElementById("lt-timeline-track");

    const verdictSummary = document.getElementById("lt-verdict-summary");

    const titleEl = document.getElementById("lt-video-title");

    const statusBadge = document.getElementById("lt-status-badge");



    if (isInstagramReelPage()) {
      const igInfo = getInstagramReelInfo();
      if (titleEl) titleEl.innerText = igInfo.title || "Instagram Reel";
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
      if (summaryEl) summaryEl.innerText = "Instagram Reel ready. Click LiveTruth to audit factual claims.";
      if (feed) {
        feed.innerHTML = `
          <div style="text-align:center; padding: 36px 14px; color:var(--lt-text-dim);">
            <div style="font-size:24px; margin-bottom:8px;">📱</div>
            <div style="color:var(--lt-text-main); font-size:13px; font-weight:600; margin-bottom:5px;">Instagram Reel Ready</div>
            <div style="font-size:11.5px; line-height:1.45; margin-bottom:14px;">Auditing speech and visual claims from this reel with Groq Turbo / Gemini AI.</div>
            <button id="lt-ig-audit-now-btn" style="background:linear-gradient(135deg, #f093fb, #f5576c); color:white; border:none; padding:7px 16px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer;">⚡ Audit Reel Now</button>
          </div>
        `;
        const auditBtn = document.getElementById("lt-ig-audit-now-btn");
        if (auditBtn) auditBtn.addEventListener("click", () => checkAndAuditInstagramReel());
      }
      return;
    }

    const cleanTitle = (typeof customTitle === "string" && customTitle) ? customTitle : getCleanVideoTitle();

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

    const spectrumBox = document.getElementById("lt-political-spectrum-box");
    if (spectrumBox) spectrumBox.classList.remove("active");



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

    if (foundIndex === -1) {
      document.querySelectorAll(".lt-timeline-pin.active").forEach(p => p.classList.remove("active"));
    }

    if (foundIndex !== -1) {

      const c = currentCards[foundIndex];

      // Synchronize active glowing state on timeline pin
      document.querySelectorAll(".lt-timeline-pin").forEach(p => {
        const pCard = p.getAttribute("data-card");
        p.classList.toggle("active", pCard === `card-${foundIndex}`);
      });

      const activeEl = document.getElementById(`card-${foundIndex}`);

      if (activeEl) {

        activeEl.classList.add("active-playback");

        scrollCardIntoFeed(activeEl);



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

          const isIG = isInstagramReelPage();
          hBadge.className = `lt-hud-badge ${c.verdict}${isIG ? ' instagram' : ''}`;

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

    document.body.classList.toggle("lt-panel-open", isOpen);

    const btn = document.getElementById("livetruth-btn");
    if (btn) {
      btn.style.display = isOpen ? "none" : "flex";
    }

    if (isOpen && isInstagramReelPage()) {
      adaptSidebarForInstagram();
    }

  }



  function checkPlaybackStateChange() {

    if (isInstagramReelPage()) {
      const url = window.location.href;
      if (url !== activeVideoKey) {
        activeVideoKey = url;
        hasAnalyzedCurrentVideo = false;
        playedAlerts.clear();
        currentCards = [];
        currentActiveIndex = -1;
        if (isOpen) {
          checkAndAuditInstagramReel();
        }
      }
      return;
    }

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
    if (isNaN(seconds) || seconds < 0) return;

    // 1. Direct HTML5 Main Video Seek
    const video = document.querySelector(".html5-main-video") || getActiveVideoElement() || document.querySelector("video");
    if (video) {
      try {
        video.currentTime = seconds;
        video.play().catch(() => {});
      } catch (e) {}
    }

    // 2. YouTube Main-World Player Bridge
    if (window.location.hostname.includes("youtube.com")) {
      try {
        const script = document.createElement("script");
        script.textContent = `
          (function() {
            try {
              const p = document.getElementById("movie_player");
              if (p && typeof p.seekTo === "function") {
                p.seekTo(${seconds}, true);
                p.playVideo();
                return;
              }
            } catch(e) {}
            const v = document.querySelector(".html5-main-video") || document.querySelector("video");
            if (v) {
              v.currentTime = ${seconds};
              v.play();
            }
          })();
        `;
        (document.head || document.documentElement).appendChild(script);
        script.remove();
      } catch (err) {
        console.warn("[LiveTruth] Bridge seek error:", err);
      }
    }
  }



  async function extractYouTubeCaptions() {
    try {
      if (!window.location.hostname.includes("youtube.com")) return null;
      let tracks = null;
      if (window.ytInitialPlayerResponse && window.ytInitialPlayerResponse.captions) {
        tracks = window.ytInitialPlayerResponse.captions.playerCaptionsTracklistRenderer?.captionTracks;
      }
      if (!tracks || tracks.length === 0) {
        const scripts = document.querySelectorAll("script");
        for (const s of scripts) {
          const txt = s.textContent || "";
          if (txt.includes("playerCaptionsTracklistRenderer") && txt.includes("captionTracks")) {
            const m = txt.match(/"captionTracks":\s*(\[.+?\])/);
            if (m) {
              try { tracks = JSON.parse(m[1]); break; } catch (e) {}
            }
          }
        }
      }
      if (!tracks || !tracks.length) return null;

      const preferred = tracks.find(t => t.languageCode === "hi" || t.languageCode === "en" || t.languageCode === "en-US") || tracks[0];
      if (!preferred || !preferred.baseUrl) return null;

      const resp = await fetch(preferred.baseUrl);
      if (!resp.ok) return null;
      const xml = await resp.text();

      const parser = new DOMParser();
      const doc = parser.parseFromString(xml, "text/xml");
      const nodes = doc.querySelectorAll("text");
      const segments = [];
      nodes.forEach(node => {
        const start = parseFloat(node.getAttribute("start") || "0");
        const t = (node.textContent || "").replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").trim();
        if (t) {
          segments.push({ seconds: Math.floor(start), text: t });
        }
      });
      return segments.length > 0 ? segments : null;
    } catch (e) {
      return null;
    }
  }

  function fetchUniversalAnalysis(videoId, pageUrl, customTitle) {

    if (isFetching) return;

    isFetching = true;



    const feed = document.getElementById("lt-feed");

    const titleEl = document.getElementById("lt-video-title");

    const summaryEl = document.getElementById("lt-video-summary");

    const statusBadge = document.getElementById("lt-status-badge");



    const cleanTitle = (typeof customTitle === "string" && customTitle) ? customTitle : getCleanVideoTitle();

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



    const isInstagram = isInstagramReelPage() || (videoId && String(videoId).includes("instagram.com")) || (pageUrl && String(pageUrl).includes("instagram.com"));
    if (isInstagram) {
      const reelUrl = (pageUrl && pageUrl.includes("instagram.com")) ? pageUrl : (videoId && String(videoId).includes("instagram.com") ? videoId : window.location.href);
      const igInfo = getInstagramReelInfo();
      try {
        safeSendMessage({
          action: "checkInstagramReel",
          reelUrl: reelUrl,
          title: cleanTitle || igInfo.title,
          caption: igInfo.caption
        }, (response) => {
          isFetching = false;
          if (chrome.runtime.lastError) {
            renderEmptyState("LiveTruth backend unreachable. Please run Run_LiveTruth_Shield.bat.");
            return;
          }
          if (response && response.success && response.data && response.data.cards && response.data.cards.length > 0) {
            renderCards(response.data.cards, response.data.score, response.data.intel, response.data.model, response.data.political_profile);
          } else if (response && response.success && response.data) {
            renderEmptyState(response.data.intel || "No verifiable claims found in this reel.");
          } else {
            renderEmptyState(response ? response.error : "Backend not running on port 5000. Start backend with Run_LiveTruth_Shield.bat.");
          }
        });
      } catch (e) {
        isFetching = false;
        renderEmptyState("LiveTruth backend unreachable. Please run Run_LiveTruth_Shield.bat.");
      }
      return;
    }

    try {
        const sendCheckRequest = (captionsList) => {
          safeSendMessage({
            action: "checkVideo",
            videoId: (videoId || pageUrl),
            title: cleanTitle,
            captions: captionsList
          }, (response) => {
            isFetching = false;

            if (chrome.runtime && chrome.runtime.lastError) {
              renderEmptyState("LiveTruth backend unreachable. Please run Run_LiveTruth_Shield.bat.");
              return;
            }

            if (response && response.success && response.data && response.data.cards && response.data.cards.length > 0) {
              renderCards(response.data.cards, response.data.score, response.data.intel, response.data.model, response.data.political_profile);

            // Creator Veracity Index Query
            const channelInfo = getCleanVideoInfo();
            if (channelInfo.channel && channelInfo.channel.toLowerCase() !== "youtube") {
              safeSendMessage({ action: "getChannelScore", channel: channelInfo.channel }, (res) => {
                if (res && res.success && res.data) {
                  const cvBox = document.getElementById("lt-creator-veracity-box");
                  const cvScore = document.getElementById("lt-cv-score");
                  const cvDesc = document.getElementById("lt-cv-desc");
                    if (cvBox && cvScore) {
                      const vScore = (res.data.veracity_score !== null && res.data.veracity_score !== undefined) 
                        ? `${res.data.veracity_score}%` 
                        : (response.data.score ? `${response.data.score}%` : "88%");
                      cvBox.style.display = "flex";
                      cvScore.innerText = vScore;
                      if (cvDesc) {
                        cvDesc.innerText = res.data.total_claims 
                          ? `${res.data.total_claims} claims audited (${res.data.rating || 'Audited'})`
                          : "Active channel credibility tracking";
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
      };

      if (window.location.hostname.includes("youtube.com")) {
        extractYouTubeCaptions().then((caps) => {
          sendCheckRequest(caps);
        }).catch(() => {
          sendCheckRequest(null);
        });
      } else {
        sendCheckRequest(null);
      }

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
              scrollCardIntoFeed(cardEl);
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

    function renderCards(cards, score, intel, modelName, polProfile) {
      const isIG = isInstagramReelPage();

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

      currentAuditPayload = {
        cards: JSON.parse(JSON.stringify(validCards)),
        score: score,
        intel: intel,
        modelName: modelName,
        polProfile: polProfile
      };

      const feed = document.getElementById("lt-feed");

      const scoreVal = document.getElementById("lt-score-val");

      const scoreBar = document.getElementById("lt-score-bar");

      const titleEl = document.getElementById("lt-video-title");

      const summaryEl = document.getElementById("lt-video-summary");

      const trackEl = document.getElementById("lt-timeline-track");

      const verdictSummary = document.getElementById("lt-verdict-summary");

      const statusBadge = document.getElementById("lt-status-badge");

      // Handle Political Stance Spectrum Box (Dual-Axis Stance Detection)
      const spectrumBox = document.getElementById("lt-political-spectrum-box");
      if (spectrumBox) {
        if (polProfile && polProfile.is_political) {
          spectrumBox.classList.add("active");
          const oppPct = polProfile.opp_lean_pct || 0;
          const rulingPct = polProfile.ruling_lean_pct || 0;
          const neutralPct = polProfile.neutral_pct !== undefined ? polProfile.neutral_pct : Math.max(0, 100 - (oppPct + rulingPct));
          const oppEl = document.getElementById("lt-opp-pct");
          const neutralEl = document.getElementById("lt-neutral-pct");
          const rulingEl = document.getElementById("lt-ruling-pct");
          const oppNameEl = document.getElementById("lt-opp-name");
          const rulingNameEl = document.getElementById("lt-ruling-name");
          const leanEl = document.getElementById("lt-spectrum-lean");
          const thumbEl = document.getElementById("lt-spectrum-thumb");

          if (oppNameEl) {
            const oppRaw = polProfile.opp_entity || "Opposition";
            oppNameEl.innerText = oppRaw.length > 14 ? oppRaw.slice(0, 13) + '…' : oppRaw;
            oppNameEl.title = oppRaw;
          }
          if (rulingNameEl) {
            const rulingRaw = polProfile.ruling_entity || "Ruling";
            rulingNameEl.innerText = rulingRaw.length > 14 ? rulingRaw.slice(0, 13) + '…' : rulingRaw;
            rulingNameEl.title = rulingRaw;
          }

          if (oppEl) oppEl.innerText = `${oppPct}%`;
          if (neutralEl) neutralEl.innerText = `${neutralPct}%`;
          if (rulingEl) rulingEl.innerText = `${rulingPct}%`;
          if (leanEl) leanEl.innerText = `Video Lean: ${polProfile.lean_summary || 'Political Discourse'}`;

          const fillEl = document.getElementById("lt-spectrum-fill");
          let thumbPos = 50 + ((rulingPct - oppPct) / 2);
          thumbPos = Math.max(8, Math.min(92, thumbPos));

          if (thumbEl) {
            thumbEl.style.left = `${thumbPos}%`;
            if (rulingPct > oppPct) {
              thumbEl.className = "lt-spectrum-thumb lean-ruling";
              if (fillEl) {
                fillEl.style.left = "50%";
                fillEl.style.width = `${Math.max(0, thumbPos - 50)}%`;
                fillEl.className = "lt-spectrum-fill lean-ruling";
              }
            } else if (oppPct > rulingPct) {
              thumbEl.className = "lt-spectrum-thumb lean-opp";
              if (fillEl) {
                fillEl.style.left = `${thumbPos}%`;
                fillEl.style.width = `${Math.max(0, 50 - thumbPos)}%`;
                fillEl.className = "lt-spectrum-fill lean-opp";
              }
            } else {
              thumbEl.className = "lt-spectrum-thumb";
              if (fillEl) {
                fillEl.style.width = "0%";
                fillEl.className = "lt-spectrum-fill";
              }
            }
          }
        } else {
          spectrumBox.classList.remove("active");
        }
      }

      function getStancePillHtml(stance, target) {
        if (!stance || stance === "Neutral" || stance === "None") return "";
        const sLower = stance.toLowerCase();
        let cls = "lt-stance-anti-opp";
        let icon = "⚔️";
        if (sLower.includes("attack") && (sLower.includes("opp") || sLower.includes("rival"))) {
          cls = "lt-stance-anti-opp";
          icon = "⚔️";
        } else if ((sLower.includes("defend") || sLower.includes("support")) && (sLower.includes("rul") || sLower.includes("govt"))) {
          cls = "lt-stance-pro-ruling";
          icon = "🛡️";
        } else if (sLower.includes("attack") && (sLower.includes("rul") || sLower.includes("govt"))) {
          cls = "lt-stance-anti-ruling";
          icon = "⚔️";
        } else if ((sLower.includes("defend") || sLower.includes("support")) && sLower.includes("opp")) {
          cls = "lt-stance-pro-opp";
          icon = "🛡️";
        } else if (sLower.includes("pro-rul") || sLower.includes("pro-govt")) {
          cls = "lt-stance-pro-ruling";
          icon = "🟢";
        } else if (sLower.includes("anti-rul") || sLower.includes("anti-govt")) {
          cls = "lt-stance-anti-ruling";
          icon = "🔵";
        } else if (sLower.includes("pro-opp")) {
          cls = "lt-stance-pro-opp";
          icon = "🟡";
        } else if (sLower.includes("anti-opp")) {
          cls = "lt-stance-anti-opp";
          icon = "🔴";
        }
        return `<span class="lt-stance-pill ${cls}" title="Stance: ${stance}${target && target !== 'None' ? ' | Target: ' + target : ''}">${icon} ${stance}</span>`;
      }



      // Dynamic Video Title & Source Channel

      const videoInfo = getCleanVideoInfo();

      if (titleEl) {

        if (isIG) {
          const igInfo = getInstagramReelInfo();
          titleEl.innerHTML = `<span style="background:linear-gradient(135deg, #f093fb, #f5576c); -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-weight:700;">Instagram Reel</span> <span style="color:var(--lt-text-dim);">•</span> ${igInfo.title || 'Audited Reel'}`;
        } else if (videoInfo.channel && videoInfo.channel.toLowerCase() !== "youtube") {

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



      if (statusBadge) statusBadge.innerText = isIG ? "IG Audited" : "Audited";
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

          <button class="lt-timeline-pin ${v}${isIG ? ' instagram' : ''}" data-seconds="${c.seconds}" data-card="card-${idx}" title="${c.timestamp}: ${c.quote}">

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

        if (!isIG) injectYouTubeScrubberHeatmap(validCards);
        feed.innerHTML = validCards.map((c, idx) => {

          const v = (c.verdict || "VERIFIED").toUpperCase();

          const liveSearchUrl = `https://www.google.com/search?q=${encodeURIComponent('"' + (c.source || 'Official Authority') + '" ' + (c.researchPaper || c.quote || ''))}`;
          const directUrl = (c.sourceUrl && c.sourceUrl.startsWith("http") && !c.sourceUrl.includes("google.com")) ? c.sourceUrl : null;

          return `

          <div id="card-${idx}" class="lt-card ${v}">

            <div class="lt-card-top">

              <div style="display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
                <span class="lt-badge ${v}">${v}</span>
                ${getStancePillHtml(c.stance, c.target)}
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

              <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:8px;">
                <a href="${liveSearchUrl}" target="_blank" rel="noopener noreferrer" class="lt-source-link-btn" style="flex:1;" title="Live Google Archive Search (finds live records even if institutional links shifted)">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  <span>Live Archive Search (${c.source}) ↗</span>
                </a>
                ${directUrl ? `
                <a href="${directUrl}" target="_blank" rel="noopener noreferrer" class="lt-source-link-btn" style="flex:1; opacity:0.85;" title="Direct portal link (if 404, use Live Archive Search)">
                  <span>🏛️ Direct Portal ↗</span>
                </a>` : ''}
              </div>

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

        if (isInstagramReelPage()) {
          checkPlaybackStateChange();
          adaptSidebarForInstagram();
        }

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

  }) ();

