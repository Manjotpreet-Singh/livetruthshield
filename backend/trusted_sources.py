"""
Source-trust assessment: only credible, checkable sources count as authentic evidence.
"""

import re
import urllib.parse

HIGH = {
    "nature.com",
    "science.org",
    "sciencedirect.com",
    "thelancet.com",
    "nejm.org",
    "jamanetwork.com",
    "bmj.com",
    "cell.com",
    "pnas.org",
    "plos.org",
    "springer.com",
    "wiley.com",
    "ieee.org",
    "acm.org",
    "arxiv.org",
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "cdc.gov",
    "fda.gov",
    "who.int",
    "nasa.gov",
    "noaa.gov",
    "nist.gov",
    "cochranelibrary.com",
    "mayoclinic.org",
    "nhs.uk",
    "ema.europa.eu",
    "ipcc.ch",
    "cern.ch",
    "esa.int",
    "isro.gov.in",
    "icmr.gov.in",
    "mohfw.gov.in",
    "un.org",
    "worldbank.org",
    "imf.org",
    "oecd.org",
    "europa.eu",
    "ourworldindata.org",
    "statista.com",
    "sec.gov",
    "federalreserve.gov",
    "bls.gov",
    "census.gov",
    "rbi.org.in",
    "data.gov.in",
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "npr.org",
    "pbs.org",
    "afp.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "economist.com",
    "aljazeera.com",
    "thehindu.com",
    "indianexpress.com",
    "hindustantimes.com",
    "ndtv.com",
    "timesofindia.indiatimes.com",
    "snopes.com",
    "factcheck.org",
    "politifact.com",
    "fullfact.org",
    "factcheck.afp.com",
    "altnews.in",
    "boomlive.in",
    "factly.in",
    "africacheck.org",
    "apple.com",
    "support.apple.com",
    "microsoft.com",
    "google.com",
    "developers.google.com",
    "tesla.com",
    "samsung.com",
    "intel.com",
    "amd.com",
    "nvidia.com",
    "openai.com",
    "anthropic.com",
    "techcrunch.com",
    "arstechnica.com",
    "theverge.com",
    "wired.com",
    "gsmarena.com",
    "anandtech.com",
}

MEDIUM = {
    "nationalgeographic.com",
    "forbes.com",
    "investopedia.com",
    "cnn.com",
    "smithsonianmag.com",
    "time.com",
    "scientificamerican.com",
    "cnbc.com",
    "britannica.com",
    "history.com",
    "newscientist.com",
    "webmd.com",
    "usatoday.com",
    "healthline.com",
    "news.google.com",
    "wikipedia.org",
}

LOW = {
    "facebook.com",
    "x.com",
    "t.me",
    "twitter.com",
    "youtu.be",
    "instagram.com",
    "reddit.com",
    "tiktok.com",
    "medium.com",
    "blogspot.com",
    "answers.com",
    "wattpad.com",
    "wordpress.com",
    "tumblr.com",
    "pinterest.com",
    "ehow.com",
    "telegram.org",
    "substack.com",
    "linkedin.com",
    "naturalnews.com",
    "quora.com",
    "buzzfeed.com",
    "youtube.com",
    "infowars.com",
    "yahoo.com",
    "whatsapp.com",
    "fandom.com",
}

GOV_EDU = re.compile(r"(\.|^)(gov|mil|edu|int)(\.[a-z]{2})?$|\.(ac|edu|gov|nic)\.[a-z]{2}$")


def _host(url_or_name: str) -> str:
    s = str(url_or_name or "").strip().lower()
    if "://" in s:
        s = urllib.parse.urlparse(s).netloc
    else:
        s = s.split("/")[0]
    s = s.split(":")[0]
    s = re.sub(r"^www\.", "", s)
    return s


def _match(host: str, group) -> bool:
    return any(host == d or host.endswith("." + d) for d in group)


def assess(url_or_name: str) -> str:
    """Returns 'high', 'medium', 'low' (known-unreliable), or 'unknown'."""
    host = _host(url_or_name)
    if not host or "." not in host:
        return "unknown"
    if _match(host, LOW):
        return "low"
    if GOV_EDU.search(host) or _match(host, HIGH):
        return "high"
    if _match(host, MEDIUM):
        return "medium"
    return "unknown"
