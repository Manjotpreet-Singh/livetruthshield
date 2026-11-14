"""
LiveTruth Shield — Multi-Model AI Engine
Supports DeepSeek (V3 & R1 Reasoner) and Google Gemini (2.5 & 2.0 Flash)
High-accuracy prompt engineering, JSON schema validation, and intelligent hybrid failover.
"""

import os
import re
import json
import asyncio
from typing import Optional, Tuple, Dict, Any
import httpx
from dotenv import load_dotenv

# Try importing google-genai
Features_Available = False
genai_client = None
genai_types = None

try:
    from google import genai
    from google.genai import types as g_types
    Features_Available = True
    genai_types = g_types
except ImportError:
    pass

# Supported Models
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro"
]

DEEPSEEK_MODELS = [
    "deepseek-chat",
    "deepseek-reasoner"
]

# State variables
DEEPSEEK_API_KEY = ""
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_MODEL_PROVIDER = "auto"
GEMINI_API_KEY = ""


def load_ai_env():
    """Reloads API keys and model configuration from .env"""
    global DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEFAULT_MODEL_PROVIDER, GEMINI_API_KEY, genai_client
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path, override=True)

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
    DEFAULT_MODEL_PROVIDER = os.getenv("DEFAULT_MODEL_PROVIDER", "auto").strip().lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    if Features_Available and GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        try:
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
            print("[+] Gemini client initialized successfully with API key.")
        except Exception as e:
            genai_client = None
            print(f"[WARNING] Could not initialize Gemini client: {e}")
    else:
        genai_client = None


# Initial load
load_ai_env()


def get_ai_status() -> Dict[str, Any]:
    """Returns the current readiness status of all configured AI models."""
    deepseek_ready = bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here")
    gemini_ready = genai_client is not None

    if deepseek_ready and gemini_ready:
        active_display = "Auto Hybrid (DeepSeek + Gemini)"
    elif deepseek_ready:
        active_display = f"DeepSeek ({DEEPSEEK_MODEL})"
    elif gemini_ready:
        active_display = "Google Gemini 2.5 Flash"
    else:
        active_display = "No API key configured"

    return {
        "status": "online",
        "thinking_level": "HIGH",
        "provider": DEFAULT_MODEL_PROVIDER,
        "active_display": active_display,
        "deepseek_configured": deepseek_ready,
        "gemini_configured": gemini_ready,
        "deepseek_model": DEEPSEEK_MODEL,
        "deepseek_base_url": DEEPSEEK_BASE_URL,
        "gemini_models": GEMINI_MODELS,
        "deepseek_models": DEEPSEEK_MODELS
    }


def save_ai_config(deepseek_key: str = None, gemini_key: str = None, provider: str = None,
                   deepseek_model: str = None, deepseek_base_url: str = None) -> Dict[str, Any]:
    """Updates API keys and preferences in .env and reloads live config."""
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

    config_map = {}
    for line in lines:
        line_s = line.strip()
        if line_s and not line_s.startswith("#") and "=" in line_s:
            k, v = line_s.split("=", 1)
            config_map[k.strip()] = v.strip()

    if gemini_key is not None and gemini_key.strip():
        config_map["GEMINI_API_KEY"] = gemini_key.strip()
    if deepseek_key is not None and deepseek_key.strip():
        config_map["DEEPSEEK_API_KEY"] = deepseek_key.strip()
    if provider is not None and provider.strip():
        config_map["DEFAULT_MODEL_PROVIDER"] = provider.strip()
    if deepseek_model is not None and deepseek_model.strip():
        config_map["DEEPSEEK_MODEL"] = deepseek_model.strip()
    if deepseek_base_url is not None and deepseek_base_url.strip():
        config_map["DEEPSEEK_BASE_URL"] = deepseek_base_url.strip()

    with open(env_file, "w", encoding="utf-8") as f:
        f.write("# LiveTruth Shield Multi-Model AI Environment Configuration\n\n")
        f.write(f"GEMINI_API_KEY={config_map.get('GEMINI_API_KEY', 'your_gemini_api_key_here')}\n")
        f.write(f"DEEPSEEK_API_KEY={config_map.get('DEEPSEEK_API_KEY', 'your_deepseek_api_key_here')}\n")
        f.write(f"DEEPSEEK_BASE_URL={config_map.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}\n")
        f.write(f"DEFAULT_MODEL_PROVIDER={config_map.get('DEFAULT_MODEL_PROVIDER', 'auto')}\n")
        f.write(f"DEEPSEEK_MODEL={config_map.get('DEEPSEEK_MODEL', 'deepseek-chat')}\n")

    load_ai_env()
    return get_ai_status()


def extract_and_parse_json(text: str) -> Dict[str, Any]:
    """Robustly cleans LLM markdown fences, <think> tags, and parses JSON."""
    if not text:
        return {}

    # Strip DeepSeek reasoning <think> ... </think> tags
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.DOTALL).strip()

    # Strip Markdown fences ```json ... ``` or ``` ... ```
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE).strip()

    # 1. Direct parse attempt
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Regex search for outer balanced {...}
    match = re.search(r'(\{[\s\S]*\})', cleaned)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    return {}


async def call_deepseek(prompt: str, system_prompt: str = None, model: str = None,
                        json_mode: bool = True, timeout: float = 80.0) -> Tuple[str, str]:
    """
    Executes a completion using DeepSeek API (OpenAI-compatible).
    Supports DeepSeek-V3 ('deepseek-chat') and DeepSeek-R1 Reasoner ('deepseek-reasoner').
    """
    global DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
    key = DEEPSEEK_API_KEY
    if not key or key == "your_deepseek_api_key_here":
        raise ValueError("DEEPSEEK_API_KEY is not configured in backend/.env")

    chosen_model = model or DEEPSEEK_MODEL or "deepseek-chat"
    base_url = DEEPSEEK_BASE_URL.rstrip("/")
    if "/chat/completions" in base_url:
        endpoint = base_url
    elif base_url.endswith("/v1"):
        endpoint = f"{base_url}/chat/completions"
    else:
        endpoint = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    sys_content = system_prompt or "You are LiveTruth Shield, an elite real-time AI fact-checking engine."
    if json_mode and "reasoner" not in chosen_model.lower():
        sys_content += " You must respond strictly with a valid JSON object matching the requested schema."

    payload = {
        "model": chosen_model,
        "messages": [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": prompt}
        ]
    }

    is_reasoner = "reasoner" in chosen_model.lower() or "r1" in chosen_model.lower()
    if is_reasoner:
        payload["max_tokens"] = 8000
    else:
        payload["temperature"] = 0.1
        payload["max_tokens"] = 4096
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

    print(f"[*] Calling DeepSeek model '{chosen_model}' at {endpoint}...")
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(endpoint, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek API HTTP {resp.status_code}: {resp.text}")

        res_data = resp.json()
        choice = res_data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        raw_content = msg.get("content", "")

        display_name = "DeepSeek-R1 (Deep Reasoner)" if is_reasoner else f"DeepSeek-V3 ({chosen_model})"
        return raw_content, display_name


_DISCOVERED = None

def discover_gemini_models() -> list:
    """Live list of text-generation Gemini models available to this API key (cached)."""
    global _DISCOVERED
    if _DISCOVERED is not None:
        return _DISCOVERED
    found = []
    try:
        for m in genai_client.models.list():
            name = (getattr(m, "name", "") or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if not name.startswith("gemini-") or (actions and "generateContent" not in actions):
                continue
            if any(x in name for x in ("embed", "tts", "image", "live", "audio", "robotics", "computer", "lite", "thinking-exp")):
                continue
            found.append(name)
        # prefer flash (fast/cheap) over pro, newest first
        found.sort(key=lambda n: ("flash" not in n, "preview" in n or "exp" in n, n), reverse=False)
        print(f"[*] Discovered Gemini models: {found[:8]}")
    except Exception as e:
        print(f"[!] Could not list Gemini models: {e}")
    _DISCOVERED = found
    return found


def extract_grounding_sources(resp) -> list:
    """Real web pages Gemini consulted via Google Search grounding."""
    out, seen = [], set()
    try:
        for cand in (resp.candidates or []):
            gm = getattr(cand, "grounding_metadata", None)
            for ch in (getattr(gm, "grounding_chunks", None) or []):
                web = getattr(ch, "web", None)
                uri = getattr(web, "uri", None)
                if uri and uri not in seen:
                    seen.add(uri)
                    out.append({"title": getattr(web, "title", "") or uri, "url": uri})
    except Exception as e:
        print(f"[!] Could not read grounding metadata: {e}")
    return out


async def call_gemini(prompt: str, preferred_model: str = None, use_search: bool = True) -> Tuple[str, str, list]:
    """
    Executes a completion using Google Gemini SDK with live search grounding and thinking fallback.
    """
    global genai_client, genai_types
    if not genai_client:
        raise ValueError("GEMINI_API_KEY is not configured or client is offline.")

    models_to_try = []
    if preferred_model and preferred_model.startswith("gemini-"):
        models_to_try.append(preferred_model)
    for m in GEMINI_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)
    # Models get retired often: also ask the API which ones this key can really use.
    for m in await asyncio.to_thread(discover_gemini_models):
        if m not in models_to_try:
            models_to_try.append(m)

    thinking_high = None
    if genai_types and hasattr(genai_types, "ThinkingConfig") and hasattr(genai_types, "ThinkingLevel"):
        try:
            thinking_high = genai_types.ThinkingConfig(thinking_level=genai_types.ThinkingLevel.HIGH)
        except Exception:
            pass

    last_err = None
    for m_name in models_to_try:
        # Tier 1: Search Grounded + Thinking
        if use_search and genai_types and hasattr(genai_types, "Tool") and hasattr(genai_types, "GoogleSearch"):
            try:
                print(f"[*] Auditing with Gemini {m_name} (Search Grounding + High Reasoning)...")
                cfg_args = {
                    "tools": [genai_types.Tool(google_search=genai_types.GoogleSearch())],
                    "temperature": 0.1
                }
                if thinking_high:
                    cfg_args["thinking_config"] = thinking_high

                resp = await asyncio.to_thread(
                    genai_client.models.generate_content,
                    model=m_name,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(**cfg_args)
                )
                if resp and resp.text:
                    return resp.text.strip(), f"{m_name} (Search Grounded)", extract_grounding_sources(resp)
            except Exception as e_search:
                last_err = e_search
                print(f"[!] {m_name} search grounding failed ({e_search}), trying direct generation...")

        # Tier 2: Direct Generation (High Reasoning)
        try:
            cfg_args = {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
            if thinking_high:
                cfg_args["thinking_config"] = thinking_high

            resp = await asyncio.to_thread(
                genai_client.models.generate_content,
                model=m_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(**cfg_args)
            )
            if resp and resp.text:
                return resp.text.strip(), f"{m_name} (High Reasoning)", []
        except Exception as e_high:
            last_err = e_high
            print(f"[!] {m_name} direct generation failed: {e_high}. Trying fast standard fallback...")

        # Tier 3: Standard generation
        try:
            resp = await asyncio.to_thread(
                genai_client.models.generate_content,
                model=m_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            if resp and resp.text:
                return resp.text.strip(), f"{m_name} (Standard)", []
        except Exception as e_std:
            last_err = e_std
            continue

    raise RuntimeError(f"All Gemini models exhausted. Last error: {last_err}")


def sanitize_and_score_cards(parsed: Dict[str, Any], title: str = "") -> Dict[str, Any]:
    """
    Cleans up, standardizes, filters ASR noise, and computes mathematically consistent truth scores.
    """
    raw_cards = parsed.get("cards", [])
    clean_cards = []

    date_intros = ("it is ", "today is ", "the date is ", "it's ", "in the year ")
    months_days = ("2024", "2025", "2026", "2027", "2028", "january", "february", "march", "april", "may",
                   "june", "july", "august", "september", "october", "november", "december", "monday", "tuesday",
                   "wednesday", "thursday", "friday", "saturday", "sunday")
    clock_terms = ("nist time", "calendar", "current date", "time.is", "clock division", "time and frequency")

    for c in raw_cards:
        if not isinstance(c, dict):
            continue

        q = str(c.get("quote", "")).strip()
        src = str(c.get("source", "")).strip()
        exp = str(c.get("explanation", "")).strip()

        if q.upper() in ["N/A", "NONE", "NULL", ""] or not q:
            continue
        if "system error" in src.lower() or "malformed" in exp.lower() or "non-existent" in exp.lower():
            continue

        # Smart noise filter: drop trivial dates and clock lookups
        clean_q = q.lower().replace('"', '').replace("'", "").strip()
        is_date_intro = any(clean_q.startswith(p) for p in date_intros) and any(w in clean_q for w in months_days)
        is_clock_source = any(k in src.lower() for k in clock_terms)
        if is_date_intro or is_clock_source:
            continue

        # Normalize verdict
        raw_v = str(c.get("verdict", "VERIFIED")).strip().upper()
        if "FALSE" in raw_v or "INCORRECT" in raw_v or "DEBUNK" in raw_v:
            verdict = "FALSE"
        elif "MISLEADING" in raw_v or "PARTIAL" in raw_v:
            verdict = "MISLEADING"
        elif "EXAGGERAT" in raw_v or "HYPERBOLE" in raw_v:
            verdict = "EXAGGERATION"
        else:
            verdict = "VERIFIED"
        c["verdict"] = verdict

        # Normalize timestamp and seconds
        ts = str(c.get("timestamp", "00:00")).strip()
        sec = c.get("seconds")
        if sec is None or not isinstance(sec, (int, float)):
            parts = ts.split(":")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                sec = int(parts[0]) * 60 + int(parts[1])
            else:
                sec = 0
        c["seconds"] = int(sec)

        if not ts or ts == "00:00" and sec > 0:
            c["timestamp"] = f"{int(sec)//60:02d}:{int(sec)%60:02d}"

        # Keep only what the model actually returned; never invent sources.
        url = str(c.get("sourceUrl", "") or "").strip()
        c["sourceUrl"] = url if url.startswith(("http://", "https://")) else ""
        c["fallacy"] = c.get("fallacy") or "None"
        c["consensus"] = c.get("consensus") or ("Consensus supports" if verdict == "VERIFIED" else "Contested / not supported")
        c["source"] = c.get("source") or "Source not cited"
        c["researchPaper"] = c.get("researchPaper") or ""
        c["researchSummary"] = c.get("researchSummary") or exp[:150]
        c["abstractPreview"] = c.get("abstractPreview") or ""
        c["dataOrigin"] = c.get("dataOrigin") or ""

        clean_cards.append(c)

    # Sort cards chronologically
    clean_cards.sort(key=lambda x: x.get("seconds", 0))

    # Compute Truth Reliability Score
    n = len(clean_cards)
    if n > 0:
        ver_count = sum(1 for x in clean_cards if x["verdict"] == "VERIFIED")
        exag_count = sum(1 for x in clean_cards if x["verdict"] == "EXAGGERATION")
        misl_count = sum(1 for x in clean_cards if x["verdict"] == "MISLEADING")
        false_count = sum(1 for x in clean_cards if x["verdict"] == "FALSE")

        # Standard reliability metric: Verified = 1.0, Exaggeration = 0.7, Misleading = 0.35, False = 0.0
        weighted_points = (ver_count * 1.0) + (exag_count * 0.70) + (misl_count * 0.35)
        computed_score = int(round((weighted_points / n) * 100))
        computed_score = max(5, min(100, computed_score))
    else:
        computed_score = 0

    parsed["cards"] = clean_cards
    parsed["score"] = computed_score

    if not clean_cards:
        parsed["intel"] = f"No substantive empirical claims extracted for '{title}'."
    elif not parsed.get("intel"):
        parsed["intel"] = f"Audited {n} claims across the timeline; {ver_count} verified."

    return parsed


async def audit_claims(text_chunk: str, title: str, video_id: str = "",
                       provider: str = None, model: str = None,
                       mode: str = "transcript", segments: list = None) -> Tuple[Dict[str, Any], str]:
    """
    High-level orchestrator: Fact-checks video dialogue with DeepSeek, Gemini, or Auto hybrid routing.
    Returns (result_dict, used_model_display_name).
    """
    if mode == "transcript":
        source_block = "REAL CAPTION TRANSCRIPT (each line starts with its [MM:SS] timestamp):\n" + text_chunk
    else:
        source_block = ("NO TRANSCRIPT IS AVAILABLE; only the title/topic above is known. Do NOT pretend to quote the video. "
                        "Instead use web search to check the main factual claims this topic/title is commonly associated with, "
                        "and use timestamp \"00:00\" and seconds 0 with the quote field set to the claim being checked. "
                        "State in 'intel' that this is a title-based check, not an audit of the spoken content.")
    audit_prompt = f"""You are LiveTruth Shield, an elite real-time AI fact-checking engine.
Perform a HIGH-ACCURACY factual audit of this video.

Media Title / Topic: {title}
{source_block}

CRITICAL AUDIT RULES:
1. VOLUME: Extract up to 14 distinct, checkable factual claims, as many as genuinely exist. Never pad. If there are none, return an empty "cards" list.
2. EXACT QUOTES & TIMESTAMPS: Quote the speaker accurately from the dialogue and include their approximate timestamp [MM:SS].
3. ANTI-PEDANTRY & ASR HOMOPHONE IMMUNITY:
   - Speech-to-text transcripts frequently contain phonetic spelling typos.
   - Do NOT flag spelling or grammar errors as FALSE. Evaluate the SPEAKER'S ACTUAL INTENDED MEANING.
4. ANTI-TRIVIA IMMUNITY:
   - Never flag conversational dates ("Today is November 3rd", "In 2026") or scene introductions as FALSE claims.
   - Focus on substantive assertions: scientific laws, product specs, economics, historical dates, statistics, security mechanisms.
5. STANDARDIZED VERDICTS: Strictly 'VERIFIED', 'MISLEADING', 'FALSE', or 'EXAGGERATION'.
6. REAL CITATIONS ONLY: Verify each claim with live web search. Put a real page you actually found in "sourceUrl". If you found no real source, leave "sourceUrl" empty and say the claim could not be verified; never invent URLs, papers or quotes.
7. COMPUTE RELIABILITY SCORE (0-100%): Calculated realistically based on verified vs misleading/false statements.

Return ONLY a valid JSON object matching this schema:
{{
  "score": 85,
  "intel": "Comprehensive summary of factual accuracy and notable errors identified.",
  "cards": [
    {{
      "verdict": "VERIFIED",
      "timestamp": "01:05",
      "seconds": 65,
      "quote": "Exact spoken quote from transcript",
      "explanation": "Authoritative explanation grounded in evidence",
      "fallacy": "None",
      "consensus": "Universal Consensus",
      "source": "Primary Authority (e.g. Nature, WHO, IEEE)",
      "sourceUrl": "https://official-authority-link",
      "researchPaper": "Formal Paper or Record Title",
      "researchSummary": "Concise summary of empirical backing",
      "abstractPreview": "Brief abstract confirming the finding.",
      "dataOrigin": "Authoritative Database Origin"
    }}
  ]
}}"""

    system_prompt = (
        "You are LiveTruth Shield's Chief Fact-Checking Engine. "
        "Audit claims with scientific rigor, peer-reviewed accuracy, and zero hallucinations. "
        "Output ONLY a valid JSON object."
    )

    deepseek_ready = bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here")
    gemini_ready = genai_client is not None

    req_provider = (provider or DEFAULT_MODEL_PROVIDER or "auto").lower()

    raw_text = None
    used_model = None
    primary_error = None
    g_sources = []

    # Determine execution strategy
    try_deepseek_first = False
    if "deepseek" in req_provider or (model and "deepseek" in model.lower()):
        try_deepseek_first = True
    elif req_provider == "gemini" or (model and "gemini" in model.lower()):
        try_deepseek_first = False
    else:  # auto
        # DeepSeek R1/V3 provides supreme reasoning & accuracy; prioritize if available
        try_deepseek_first = deepseek_ready

    # Attempt 1
    if try_deepseek_first and deepseek_ready:
        try:
            target_ds_model = model if (model and "deepseek" in model.lower()) else DEEPSEEK_MODEL
            raw_text, used_model = await call_deepseek(audit_prompt, system_prompt=system_prompt, model=target_ds_model)
        except Exception as e_ds:
            primary_error = e_ds
            print(f"[!] DeepSeek audit failed: {e_ds}. Attempting fallback...")

    elif not try_deepseek_first and gemini_ready:
        try:
            target_gem_model = model if (model and "gemini" in model.lower()) else "gemini-2.5-flash"
            raw_text, used_model, g_sources = await call_gemini(audit_prompt, preferred_model=target_gem_model, use_search=True)
        except Exception as e_gem:
            primary_error = e_gem
            print(f"[!] Gemini audit failed: {e_gem}. Attempting fallback...")

    # Attempt 2 (Failover / Alternate Provider)
    if not raw_text:
        if try_deepseek_first and gemini_ready:
            try:
                print("[*] Failing over to Google Gemini 2.5 Flash...")
                raw_text, used_model, g_sources = await call_gemini(audit_prompt, preferred_model="gemini-2.5-flash", use_search=True)
            except Exception as e_gem_fall:
                print(f"[!] Gemini failover failed: {e_gem_fall}")
        elif not try_deepseek_first and deepseek_ready:
            try:
                print("[*] Failing over to DeepSeek...")
                raw_text, used_model = await call_deepseek(audit_prompt, system_prompt=system_prompt, model=DEEPSEEK_MODEL)
            except Exception as e_ds_fall:
                print(f"[!] DeepSeek failover failed: {e_ds_fall}")

    if not raw_text:
        err_msg = str(primary_error or "Both DeepSeek and Gemini are unconfigured or unavailable.")
        raise RuntimeError(f"AI Fact-checking failed: {err_msg}")

    parsed = extract_and_parse_json(raw_text)
    if not parsed or not isinstance(parsed, dict) or "cards" not in parsed:
        raise ValueError(f"Model output could not be parsed into valid fact-checking schema: {raw_text[:200]}")

    sanitized = sanitize_and_score_cards(parsed, title=title)
    sanitized["model"] = used_model
    sanitized["provider"] = "deepseek" if "deepseek" in used_model.lower() else "gemini"
    sanitized["thinking_level"] = "HIGH"
    sanitized["mode"] = mode
    sanitized["sources"] = g_sources
    if mode != "transcript":
        sanitized["intel"] = "[Title-based check, no transcript analysed] " + str(sanitized.get("intel", ""))

    return sanitized, used_model


async def ask_assistant(question: str, video_id: str = "", timestamp: str = "00:00",
                        title: str = "", cards: list = None, intel: str = "",
                        provider: str = None, model: str = None) -> Tuple[str, str]:
    """
    Answers user questions about the video facts using DeepSeek or Gemini.
    """
    cards = cards or []
    cards_summary = "\n".join([
        f"- [{c.get('verdict')}] at {c.get('timestamp')}: \"{c.get('quote')}\" -> {c.get('explanation')} (Source: {c.get('source')}, Fallacy: {c.get('fallacy', 'None')})"
        for c in cards[:8]
    ])

    ask_prompt = f"""You are LiveTruth Shield's in-player real-time fact-checking assistant.
A viewer is watching a video titled "{title}" (Video ID: {video_id}) around timestamp [{timestamp}].
Audited Topic Intel: {intel}
Audited Timeline Claims:
{cards_summary}

The viewer asks: "{question}"

Instructions:
1. Provide a direct, authoritative, and scientifically rigorous explanation in 2 to 3 concise sentences.
2. Ground your answer in primary scientific consensus (e.g. PubMed, WHO, IEEE, Nature, UN).
3. If the viewer asks about a specific misconception or fallacy, clearly state what the empirical reality is.
4. Keep the tone helpful, objective, and sharp. Do NOT include conversational filler like 'Sure!' or 'Here is your answer'."""

    deepseek_ready = bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here")
    gemini_ready = genai_client is not None
    req_provider = (provider or DEFAULT_MODEL_PROVIDER or "auto").lower()

    # Prioritize DeepSeek if requested or in auto mode with key
    if ("deepseek" in req_provider or req_provider == "auto") and deepseek_ready:
        try:
            target_ds = model if (model and "deepseek" in model.lower()) else "deepseek-chat"
            answer, m_display = await call_deepseek(ask_prompt, model=target_ds, json_mode=False)
            return answer.strip(), m_display
        except Exception as e:
            print(f"[!] DeepSeek ask failed ({e}), falling back to Gemini...")

    if gemini_ready:
        try:
            target_gem = model if (model and "gemini" in model.lower()) else "gemini-2.5-flash"
            resp = await asyncio.to_thread(
                genai_client.models.generate_content,
                model=target_gem,
                contents=ask_prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())])
            )
            if resp and resp.text:
                return resp.text.strip(), f"{target_gem} (Assistant)"
        except Exception as e:
            print(f"[!] Gemini ask failed ({e})")

    raise RuntimeError("No configured AI model could answer (check API keys / quota).")
