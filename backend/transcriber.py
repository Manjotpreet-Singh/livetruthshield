"""
Universal transcript pipeline for LiveTruth Shield.

Order of attempts (first success wins):
  1. YouTube captions (youtube-transcript-api)         - fast, free
  2. Platform captions/subtitles via yt-dlp            - Vimeo, TikTok, X, Facebook, Twitch VODs, ... when present
  3. Speech-to-text of the real audio:
       a. Gemini audio understanding (uses your GEMINI_API_KEY, nothing extra to install)
       b. faster-whisper running locally (optional: pip install faster-whisper)
Audio/video download uses yt-dlp, which supports YouTube, Instagram, Twitch, TikTok, X/Twitter,
Facebook, Reddit, Vimeo, Dailymotion, Kick, Rumble and ~1000 other sites. ffmpeg is recommended.
"""
import os
import re
import json
import glob
import shutil
import asyncio
import tempfile
import mimetypes
import subprocess
import urllib.request

MAX_MINUTES = int(os.getenv("MAX_AUDIO_MINUTES", "180"))
LIVE_SECONDS = int(os.getenv("LIVE_CAPTURE_SECONDS", "120"))


def _ydl_base_opts() -> dict:
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 30, "retries": 3}
    cookies_file = os.getenv("YTDLP_COOKIES_FILE", "").strip()
    browser = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()  # e.g. chrome, edge, firefox
    if cookies_file and os.path.exists(cookies_file):
        opts["cookiefile"] = cookies_file
    elif browser:
        opts["cookiesfrombrowser"] = (browser,)
    return opts


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


# ---------------------------------------------------------------- captions via yt-dlp
def _parse_json3(raw: str):
    segs = []
    for ev in json.loads(raw).get("events", []):
        t = _clean("".join(s.get("utf8", "") for s in ev.get("segs", []) or []))
        if t:
            segs.append((int(ev.get("tStartMs", 0) / 1000), t))
    return segs


def _ts_to_sec(ts: str) -> int:
    parts = ts.replace(",", ".").split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return int(parts[0] * 3600 + parts[1] * 60 + parts[2])


def _parse_vtt(raw: str):
    segs, last = [], ""
    for block in re.split(r"\n\s*\n", raw):
        m = re.search(r"([\d:.,]+)\s*-->\s*[\d:.,]+", block)
        if not m:
            continue
        lines = [l for l in block.splitlines() if "-->" not in l and not l.strip().isdigit() and l.strip() != "WEBVTT"]
        t = _clean(" ".join(lines))
        if t and t != last:
            segs.append((_ts_to_sec(m.group(1)), t))
            last = t
    return segs


def _pick_track(tracks: dict):
    if not tracks:
        return None
    langs = sorted(tracks.keys(), key=lambda k: (not k.lower().startswith("en"), "-orig" not in k, k))
    for lang in langs:
        fmts = {f.get("ext"): f for f in tracks[lang] if f.get("url")}
        for ext in ("json3", "vtt"):
            if ext in fmts:
                return ext, fmts[ext]["url"]
    return None


def _ytdlp_info_and_captions(url: str):
    import yt_dlp  # noqa
    with yt_dlp.YoutubeDL({**_ydl_base_opts(), "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    meta = {
        "title": info.get("title") or "",
        "channel": info.get("uploader") or info.get("channel") or "",
        "duration": info.get("duration") or 0,
        "is_live": bool(info.get("is_live")),
    }
    pick = _pick_track(info.get("subtitles") or {}) or _pick_track(info.get("automatic_captions") or {})
    segs = []
    if pick:
        ext, turl = pick
        req = urllib.request.Request(turl, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        segs = _parse_json3(raw) if ext == "json3" else _parse_vtt(raw)
    return meta, segs


# ---------------------------------------------------------------- audio download
def _download_audio(url: str, workdir: str, duration: int) -> str:
    import yt_dlp
    if duration and duration > MAX_MINUTES * 60:
        raise RuntimeError(f"Video is {duration // 60} min long; limit is {MAX_MINUTES} min (set MAX_AUDIO_MINUTES in .env).")
    opts = {**_ydl_base_opts(), "format": "bestaudio/best", "outtmpl": os.path.join(workdir, "src.%(ext)s"),
            "match_filter": yt_dlp.utils.match_filter_func("!is_live")}  # never record a live stream forever
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    files = [f for f in glob.glob(os.path.join(workdir, "src.*")) if not f.endswith((".part", ".ytdl"))]
    if not files:
        raise RuntimeError("Download produced no media file.")
    return files[0]


def _capture_live(url: str, workdir: str, seconds: int) -> str:
    """Record the next `seconds` of a LIVE stream's audio (Twitch, Kick, YouTube Live, X Spaces, ...)."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required to capture live streams (winget install Gyan.FFmpeg)")
    out = os.path.join(workdir, "live.mp3")
    enc = ["-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k", out]
    errs = []
    # A) direct stream URL resolved by yt-dlp
    try:
        import yt_dlp
        opts = {**_ydl_base_opts(), "format": "bestaudio/worst", "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        stream = info.get("url") or ((info.get("requested_formats") or [{}])[0].get("url"))
        headers = "".join(f"{k}: {v}\r\n" for k, v in (info.get("http_headers") or {}).items())
        if stream:
            cmd = ["ffmpeg", "-y", "-headers", headers, "-i", stream, "-t", str(seconds)] + enc
            subprocess.run(cmd, check=True, capture_output=True, timeout=seconds + 180)
            if os.path.exists(out) and os.path.getsize(out) > 2000:
                return out
    except Exception as e:
        errs.append(f"yt-dlp live: {str(e).splitlines()[-1][:150]}")
    # B) streamlink (specialist live-stream tool, optional: pip install streamlink)
    if shutil.which("streamlink"):
        try:
            sl = subprocess.Popen(["streamlink", "--stdout", "--quiet", url, "audio_only,worst"],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                subprocess.run(["ffmpeg", "-y", "-i", "pipe:0", "-t", str(seconds)] + enc, stdin=sl.stdout,
                               check=True, capture_output=True, timeout=seconds + 180)
            finally:
                sl.kill()
            if os.path.exists(out) and os.path.getsize(out) > 2000:
                return out
        except Exception as e:
            errs.append(f"streamlink: {str(e).splitlines()[-1][:150] if str(e) else 'failed'}")
    else:
        errs.append("streamlink not installed (optional: pip install streamlink)")
    raise RuntimeError("could not capture the live stream (" + "; ".join(errs) + ")")


def _compress_audio(path: str, workdir: str) -> str:
    """Mono 16 kHz 32 kbps mp3: small, fast to upload, ideal for speech. Needs ffmpeg."""
    if not shutil.which("ffmpeg"):
        return path
    out = os.path.join(workdir, "speech.mp3")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k", out],
                       check=True, capture_output=True, timeout=900)
        return out
    except Exception as e:
        print(f"[!] ffmpeg compression failed ({e}); using original file.")
        return path


# ---------------------------------------------------------------- speech to text
def _whisper_local(path: str):
    from faster_whisper import WhisperModel  # optional dependency
    model = WhisperModel(os.getenv("WHISPER_MODEL", "base"), compute_type="int8")
    segments, _ = model.transcribe(path, vad_filter=True)
    return [(int(s.start), _clean(s.text)) for s in segments if _clean(s.text)]


async def _speech_to_text(path: str, errors: list):
    import ai_engine
    if ai_engine.genai_client is not None:
        try:
            segs = await ai_engine.transcribe_audio_gemini(path)
            if segs:
                return segs, "speech-to-text (Gemini)"
            errors.append("Gemini returned an empty transcript (no speech?)")
        except Exception as e:
            errors.append(f"Gemini transcription failed: {e}")
    try:
        import faster_whisper  # noqa
    except ImportError:
        errors.append("Local Whisper not installed (optional: pip install faster-whisper)")
        return [], ""
    try:
        segs = await asyncio.to_thread(_whisper_local, path)
        if segs:
            return segs, "speech-to-text (local Whisper)"
    except Exception as e:
        errors.append(f"Local Whisper failed: {e}")
    return [], ""


# ---------------------------------------------------------------- public entry
async def get_transcript(source_url: str = "", youtube_id: str = "", local_path: str = "", yt_captions=None) -> dict:
    """Returns {segments, method, title, channel, error}."""
    res = {"segments": [], "method": "", "title": "", "channel": "", "error": ""}
    errors, meta = [], {}

    if not local_path:
        # 1. YouTube captions
        if youtube_id and yt_captions:
            segs, err = await asyncio.to_thread(yt_captions, youtube_id)
            if segs:
                res.update(segments=segs, method="YouTube captions")
                return res
            errors.append(f"No YouTube captions ({err})")

        # 2. yt-dlp metadata + platform captions
        try:
            import yt_dlp  # noqa
            have_ytdlp = True
        except ImportError:
            have_ytdlp = False
            errors.append("yt-dlp not installed (run: pip install yt-dlp)")
        if have_ytdlp:
            try:
                meta, segs = await asyncio.to_thread(_ytdlp_info_and_captions, source_url)
                res["title"], res["channel"] = meta.get("title", ""), meta.get("channel", "")
                if segs and not meta.get("is_live"):
                    res.update(segments=segs, method="platform captions (yt-dlp)")
                    return res
                errors.append("platform has no captions")
            except Exception as e:
                errors.append(f"yt-dlp info failed: {str(e).splitlines()[-1][:200]}")
        if not have_ytdlp:
            res["error"] = "; ".join(errors)
            return res

    # 3. Real audio -> speech-to-text
    workdir = tempfile.mkdtemp(prefix="livetruth_")
    live_note = ""
    try:
        try:
            live_note = ""
            if local_path:
                media = local_path
            elif meta.get("is_live"):
                media = await asyncio.to_thread(_capture_live, source_url, workdir, LIVE_SECONDS)
                live_note = f" - LIVE: {LIVE_SECONDS}s sample, timestamps relative to capture start"
            else:
                try:
                    media = await asyncio.to_thread(_download_audio, source_url, workdir, meta.get("duration", 0))
                except Exception as dl_err:
                    if meta:  # known to be a normal video: genuine failure
                        raise
                    # metadata lookup failed too: it may be a live stream, try capturing it
                    media = await asyncio.to_thread(_capture_live, source_url, workdir, LIVE_SECONDS)
                    live_note = f" - LIVE: {LIVE_SECONDS}s sample, timestamps relative to capture start"
            media = await asyncio.to_thread(_compress_audio, media, workdir)
        except Exception as e:
            errors.append(f"audio download failed: {str(e).splitlines()[-1][:250]}")
            res["error"] = "; ".join(errors)
            return res
        segs, method = await _speech_to_text(media, errors)
        if segs:
            res.update(segments=segs, method=method + live_note)
        else:
            res["error"] = "; ".join(errors)
        return res
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
