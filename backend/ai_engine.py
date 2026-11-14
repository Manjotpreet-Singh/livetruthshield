"""
LiveTruth Shield — Multi-Model AI Engine (High-Speed Turbo & Deep Reasoning)
Supports Groq (Llama 3.3 70B & DeepSeek-R1), Official DeepSeek, and Google Gemini.
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
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash"
]

DEEPSEEK_MODELS = [
    "deepseek-chat",
    "deepseek-reasoner"
]

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "llama-3.1-8b-instant"
]

# State variables
DEEPSEEK_API_KEY = ""
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_MODEL_PROVIDER = "groq"
GEMINI_API_KEY = ""
GROQ_API_KEY = ""
GROQ_MODEL = "llama-3.3-70b-versatile"

# Persistent HTTP Client for zero-latency SSL connection reuse
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(45.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=15, max_connections=30)
        )
    return _http_client


def load_ai_env():
    """Reloads API keys and model configuration from .env"""
    global DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEFAULT_MODEL_PROVIDER
    global GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL, genai_client
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path, override=True)

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
    DEFAULT_MODEL_PROVIDER = os.getenv("DEFAULT_MODEL_PROVIDER", "groq").strip().lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
        print(f"[+] Groq AI Engine active (Model: {GROQ_MODEL} - Turbo Speed).")

    if Features_Available and GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        try:
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
            print("[+] Gemini client initialized successfully.")
        except Exception as e:
            genai_client = None
            print(f"[WARNING] Could not initialize Gemini client: {e}")
    else:
        genai_client = None


# Initial load
load_ai_env()


def get_ai_status() -> Dict[str, Any]:
    """Returns the current readiness status of all configured AI models."""
    groq_ready = bool(GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"))
    deepseek_ready = bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here")
    gemini_ready = genai_client is not None

    if groq_ready:
        active_display = f"Groq {GROQ_MODEL} (Turbo High-Speed)"
    elif deepseek_ready and gemini_ready:
        active_display = "Auto Hybrid (DeepSeek + Gemini)"
    elif deepseek_ready:
        active_display = f"DeepSeek ({DEEPSEEK_MODEL})"
    elif gemini_ready:
        active_display = "Google Gemini 3.8 Flash"
    else:
        active_display = "No API key configured"

    return {
        "status": "online",
        "thinking_level": "HIGH",
        "provider": DEFAULT_MODEL_PROVIDER,
        "active_display": active_display,
        "groq_configured": groq_ready,
        "deepseek_configured": deepseek_ready,
        "gemini_configured": gemini_ready,
        "groq_model": GROQ_MODEL,
        "deepseek_model": DEEPSEEK_MODEL,
        "deepseek_base_url": DEEPSEEK_BASE_URL,
        "gemini_models": GEMINI_MODELS,
        "deepseek_models": DEEPSEEK_MODELS
    }


def save_ai_config(groq_key: str = None, deepseek_key: str = None, gemini_key: str = None,
                   groq_model: str = None, provider: str = None,
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

    if groq_key is not None and groq_key.strip():
        config_map["GROQ_API_KEY"] = groq_key.strip()
    if groq_model is not None and groq_model.strip():
        config_map["GROQ_MODEL"] = groq_model.strip()
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
        f.write(f"GROQ_API_KEY={config_map.get('GROQ_API_KEY', '')}\n")
        f.write(f"GROQ_MODEL={config_map.get('GROQ_MODEL', 'llama-3.3-70b-versatile')}\n")
        f.write(f"DEEPSEEK_API_KEY={config_map.get('DEEPSEEK_API_KEY', 'your_deepseek_api_key_here')}\n")
        f.write(f"GEMINI_API_KEY={config_map.get('GEMINI_API_KEY', 'your_gemini_api_key_here')}\n")
        f.write(f"DEFAULT_MODEL_PROVIDER={config_map.get('DEFAULT_MODEL_PROVIDER', 'groq')}\n")
        f.write(f"DEEPSEEK_BASE_URL={config_map.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')}\n")
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


async def call_groq(prompt: str, system_prompt: str = None, json_mode: bool = True,
                    model: str = None, max_tokens: int = 2048, timeout: float = 35.0) -> Tuple[str, str]:
    """
    Executes fact-checking using Groq Cloud's ultra-fast LPUs.
    Sub-second time-to-first-token, 300+ tokens/sec, and 100% free with no 404/quota issues.
    """
    global GROQ_API_KEY, GROQ_MODEL
    key = GROQ_API_KEY
    if not key or not key.startswith("gsk_"):
        raise ValueError("GROQ_API_KEY is not configured in backend/.env")

    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    sys_content = system_prompt or "You are LiveTruth Shield, an elite real-time AI fact-checking engine."
    if json_mode:
        sys_content += " You must respond strictly with a valid JSON object matching the requested schema."

    # Priority model sequence: Chosen model -> llama-3.3-70b-versatile -> deepseek-r1 -> llama-3.1-8b-instant
    primary_m = model or GROQ_MODEL or "llama-3.3-70b-versatile"
    candidate_models = [primary_m]
    for fallback_m in ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "llama-3.1-8b-instant"]:
        if fallback_m not in candidate_models:
            candidate_models.append(fallback_m)

    client = get_http_client()
    last_err = None

    for m_name in candidate_models:
        payload = {
            "model": m_name,
            "messages": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.15,
            "max_tokens": max_tokens
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        print(f"[*] Auditing with Groq '{m_name}' (Turbo Speed)...")
        try:
            resp = await client.post(endpoint, headers=headers, json=payload, timeout=timeout)
            if resp.status_code == 200:
                res_data = resp.json()
                choice = res_data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                raw_content = msg.get("content", "")
                display_name = f"Groq {m_name} (Turbo Speed)"
                return raw_content, display_name
            else:
                last_err = f"Groq HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[!] Groq {m_name} error: {last_err}. Trying alternate...")
        except Exception as e:
            last_err = str(e)
            print(f"[!] Groq {m_name} exception: {e}. Trying alternate...")

    raise RuntimeError(f"All Groq models failed. Last error: {last_err}")


async def call_deepseek(prompt: str, system_prompt: str = None, model: str = None,
                        json_mode: bool = True, timeout: float = 60.0) -> Tuple[str, str]:
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
    endpoint = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url

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
        payload["max_tokens"] = 6000
    else:
        payload["temperature"] = 0.1
        payload["max_tokens"] = 3000
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

    print(f"[*] Calling DeepSeek model '{chosen_model}'...")
    client = get_http_client()
    resp = await client.post(endpoint, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API HTTP {resp.status_code}: {resp.text}")

    res_data = resp.json()
    choice = res_data.get("choices", [{}])[0]
    msg = choice.get("message", {})
    raw_content = msg.get("content", "")

    display_name = "DeepSeek-R1 (Reasoner)" if is_reasoner else f"DeepSeek-V3 ({chosen_model})"
    return raw_content, display_name


async def call_gemini(prompt: str, preferred_model: str = None) -> Tuple[str, str, list]:
    """
    Executes a completion using Google Gemini SDK with active models.
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

    last_err = None
    for m_name in models_to_try:
        try:
            print(f"[*] Auditing with Gemini {m_name}...")
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
                return resp.text.strip(), f"{m_name} (Gemini)", []
        except Exception as e:
            last_err = e
            print(f"[!] Gemini {m_name} failed: {e}. Trying next...")

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

        # Clean fields
        url = str(c.get("sourceUrl", "") or "").strip()
        c["sourceUrl"] = url if url.startswith(("http://", "https://")) else ""
        c["fallacy"] = c.get("fallacy") or "None"
        c["consensus"] = c.get("consensus") or ("Consensus supports" if verdict == "VERIFIED" else "Contested / not supported")
        c["source"] = c.get("source") or "Empirical Authority"
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

        # Standard reliability metric
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
    High-level orchestrator: Fact-checks video dialogue with Groq (Turbo), DeepSeek, or Gemini.
    Returns (result_dict, used_model_display_name).
    """
    if mode == "transcript":
        source_block = "REAL CAPTION TRANSCRIPT (each line starts with its [MM:SS] timestamp):\n" + text_chunk
    else:
        source_block = ("NO TRANSCRIPT IS AVAILABLE; only the title/topic above is known. "
                        "Check the main factual claims this topic/title is commonly associated with. "
                        "Use timestamp \"00:00\" and seconds 0 with the quote set to the claim being checked.")

    audit_prompt = f"""You are LiveTruth Shield, an elite real-time AI fact-checking engine.
Perform a HIGH-ACCURACY, FAST factual audit of this media.

Media Title / Topic: {title}
{source_block}

CRITICAL AUDIT RULES:
1. VOLUME: Extract 6 to 12 distinct, checkable factual claims. If there are none, return an empty "cards" list.
2. EXACT QUOTES & TIMESTAMPS: Quote the speaker accurately from the dialogue and include their approximate timestamp [MM:SS].
3. ANTI-PEDANTRY: Speech-to-text transcripts frequently contain phonetic spelling typos. Evaluate the SPEAKER'S ACTUAL INTENDED MEANING.
4. ANTI-TRIVIA: Never flag conversational dates ("Today is November 3rd") as FALSE claims. Focus on substantive assertions: scientific laws, product specs, economics, historical dates, statistics, security mechanisms.
5. STANDARDIZED VERDICTS: Strictly 'VERIFIED', 'MISLEADING', 'FALSE', or 'EXAGGERATION'.
6. CITATIONS: Attribute each claim to an authoritative body (e.g., IEEE, Nature, WHO, NIST, NASA).
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
        "Audit claims with scientific rigor, speed, and peer-reviewed accuracy. "
        "Output ONLY a valid JSON object."
    )

    groq_ready = bool(GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"))
    deepseek_ready = bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here")
    gemini_ready = genai_client is not None

    req_provider = (provider or DEFAULT_MODEL_PROVIDER or "groq").lower()

    raw_text = None
    used_model = None
    primary_error = None
    g_sources = []

    # Priority 1: Groq LPUs (Fastest: ~1.5 seconds)
    if (groq_ready and req_provider in ("auto", "groq", "deepseek")) or "groq" in req_provider:
        try:
            raw_text, used_model = await call_groq(audit_prompt, system_prompt=system_prompt, model=model)
        except Exception as e_groq:
            primary_error = e_groq
            print(f"[!] Groq audit failed: {e_groq}. Attempting fallback...")

    # Priority 2: Official DeepSeek (if Groq unconfigured or failed)
    if not raw_text and deepseek_ready and ("deepseek" in req_provider or req_provider == "auto"):
        try:
            target_ds_model = model if (model and "deepseek" in model.lower()) else DEEPSEEK_MODEL
            raw_text, used_model = await call_deepseek(audit_prompt, system_prompt=system_prompt, model=target_ds_model)
        except Exception as e_ds:
            primary_error = e_ds
            print(f"[!] DeepSeek audit failed: {e_ds}. Attempting fallback...")

    # Priority 3: Google Gemini (if DeepSeek/Groq unconfigured or failed)
    if not raw_text and gemini_ready:
        try:
            target_gem_model = model if (model and "gemini" in model.lower()) else "gemini-3.8-flash"
            raw_text, used_model, g_sources = await call_gemini(audit_prompt, preferred_model=target_gem_model)
        except Exception as e_gem:
            primary_error = e_gem
            print(f"[!] Gemini audit failed: {e_gem}")

    if not raw_text:
        err_msg = str(primary_error or "All AI engines are unconfigured or unavailable.")
        raise RuntimeError(f"AI Fact-checking failed: {err_msg}")

    parsed = extract_and_parse_json(raw_text)
    if not parsed or not isinstance(parsed, dict) or "cards" not in parsed:
        raise ValueError(f"Model output could not be parsed into valid fact-checking schema: {raw_text[:200]}")

    sanitized = sanitize_and_score_cards(parsed, title=title)
    sanitized["model"] = used_model
    sanitized["provider"] = "groq" if "groq" in used_model.lower() else ("deepseek" if "deepseek" in used_model.lower() else "gemini")
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
    Answers user questions about the video facts using Groq (Instant), DeepSeek, or Gemini.
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

    groq_ready = bool(GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"))
    deepseek_ready = bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here")
    gemini_ready = genai_client is not None
    req_provider = (provider or DEFAULT_MODEL_PROVIDER or "groq").lower()

    # Priority 1: Groq (ultra fast, ~0.6s)
    if (groq_ready and req_provider in ("auto", "groq", "deepseek")) or "groq" in req_provider:
        try:
            raw_ans, m_display = await call_groq(ask_prompt, json_mode=False, max_tokens=512)
            clean_ans = re.sub(r'<think>[\s\S]*?</think>', '', raw_ans, flags=re.DOTALL).strip()
            return clean_ans, m_display
        except Exception as e_groq:
            print(f"[!] Groq assistant failed ({e_groq}), trying fallback...")

    # Priority 2: DeepSeek
    if ("deepseek" in req_provider or req_provider == "auto") and deepseek_ready:
        try:
            target_ds = model if (model and "deepseek" in model.lower()) else "deepseek-chat"
            answer, m_display = await call_deepseek(ask_prompt, model=target_ds, json_mode=False)
            return answer.strip(), m_display
        except Exception as e:
            print(f"[!] DeepSeek ask failed ({e}), falling back to Gemini...")

    # Priority 3: Gemini fallback
    if gemini_ready:
        for m_name in ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]:
            try:
                resp = await asyncio.to_thread(
                    genai_client.models.generate_content,
                    model=m_name,
                    contents=ask_prompt,
                    config=genai_types.GenerateContentConfig(temperature=0.2)
                )
                if resp and resp.text:
                    return resp.text.strip(), f"{m_name} (Assistant)"
            except Exception as e:
                print(f"[!] Gemini {m_name} ask failed ({e})")

    raise RuntimeError("No configured AI model could answer (check API keys / quota).")
