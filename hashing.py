# hashing.py
import hashlib

HASH_VERSION = "v1"

def normalize_articles(articles: list[dict]) -> str:
    """
    Convert articles into a stable, deterministic string.
    """
    lines = []
    for a in articles:
        lines.append(f"{a['date']}|{a['headline']}|{a['url']}")
    return "\n".join(lines)

def compute_articles_hash(articles: list[dict]) -> str:
    normalized = normalize_articles(articles)
    payload = f"{HASH_VERSION}\n{normalized}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

