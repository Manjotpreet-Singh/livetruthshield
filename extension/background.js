chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  const fetchWithFallback = (path, options = {}) => {
    const primary = `http://127.0.0.1:5000${path}`;
    const fallback = `http://localhost:5000${path}`;
    return fetch(primary, options)
      .catch(() => fetch(fallback, options))
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      });
  };

  if (request.action === "checkVideo") {
    const videoId = request.videoId;
    const title = request.title || "";
    const path = `/api/check?v=${encodeURIComponent(videoId)}&title=${encodeURIComponent(title)}&channel=${encodeURIComponent(request.channel || "")}`;

    fetchWithFallback(path)
      .then(data => sendResponse({ success: true, data: data }))
      .catch(err => {
        console.warn("[LiveTruth] Backend unreachable on port 5000:", err.message);
        sendResponse({
          success: false,
          error: "Backend server is not running on port 5000. Start backend with start.bat."
        });
      });
    return true;
  }

  if (request.action === "askQuestion") {
    const payload = {
      question: request.question || "",
      video_id: request.videoId || "",
      title: request.title || "",
      timestamp: request.timestamp || ""
    };

    fetchWithFallback("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(data => sendResponse({ success: true, data: data }))
      .catch(err => {
        console.warn("[LiveTruth] Ask API error:", err.message);
        sendResponse({
          success: false,
          error: "Could not connect to Gemini Assistant. Ensure backend is running."
        });
      });
    return true;
  }

  if (request.action === "getChannelScore") {
    const channel = request.channel || "";
    const path = `/api/channel-score?channel=${encodeURIComponent(channel)}`;

    fetchWithFallback(path)
      .then(data => sendResponse({ success: true, data: data }))
      .catch(err => {
        sendResponse({ success: false, error: err.message });
      });
    return true;
  }
});
