from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import json
from urllib.parse import urljoin
import requests
import unicodedata
from pathlib import Path
import time

# ----------------------------
# Configuration
# ----------------------------
DATE_REGEX = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE
)
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


# ----------------------------
# HTML Linearization
# ----------------------------
def linearize_html(html: str) -> str:
    """Convert HTML to clean line-based text."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, and common UI elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text("\n")
    # Strip blank lines
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text

# ----------------------------
# Cleaning
# ----------------------------
def clean_lines(lines: List[str]) -> List[str]:
    """Remove obvious UI or pagination noise."""
    cleaned = []
    for line in lines:
        if re.search(r"(filter|showing \d+ of|back to top|close)", line, re.I):
            continue
        cleaned.append(line)
    return cleaned

# ----------------------------
# Press region extraction
# ----------------------------
def extract_press_region(html: str, padding: int = 2) -> str:
    """
    Crop HTML to only include the press region (dense cluster of dates + headlines).
    Returns HTML string.
    """
    linear_text = linearize_html(html)
    lines = linear_text.splitlines()

    # Find date lines
    date_indices = [i for i, line in enumerate(lines) if DATE_REGEX.search(line)]
    if not date_indices:
        return html  # fallback: return full HTML

    start = max(0, date_indices[0] - padding)
    end = min(len(lines), date_indices[-1] + padding + 1)
    cropped_lines = lines[start:end]
    cleaned_lines = clean_lines(cropped_lines)

    print(f"[DEBUG] Date lines: {date_indices}")
    print(f"[DEBUG] Cropped {len(cropped_lines)} lines, cleaned {len(cleaned_lines)} lines")

    # Build a minimal HTML with only the relevant <a> tags that match cleaned lines
    soup = BeautifulSoup(html, "html.parser")
    press_html = BeautifulSoup("", "html.parser")
    cleaned_set = set(cleaned_lines)
    matches = 0

    for tag in soup.find_all(["a", "p", "div", "span"], recursive=True):
        text = tag.get_text(strip=True)
        if any(cl in text for cl in cleaned_set):
            press_html.append(tag)
            matches += 1

    print(f"[DEBUG] Tags matched in press region: {matches}")
    return str(press_html)

# ----------------------------
# Article extraction (line-based)
# ----------------------------
def extract_articles_from_lines(html: str, base_url: str) -> List[Dict]:
    """
    Extract articles by scanning lines in order.
    Each date applies to the headlines that follow until a new date appears.
    """
    linear_text = linearize_html(html)
    lines = linear_text.splitlines()
    lines = clean_lines(lines)

    # For mapping URLs, build a lookup of text -> href
    soup = BeautifulSoup(html, "html.parser")
    link_lookup = {}
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if text:
            href = a["href"]
            if href.startswith("/"):
                href = base_url + href
            link_lookup[text] = href

    articles = []
    current_date = None

    for line in lines:
        # Detect date
        match = DATE_REGEX.search(line)
        if match:
            current_date = match.group().strip()
            print(f"[DEBUG] Found date: {current_date}")
            continue

        # Skip noise
        if re.search(r"(filter|showing \d+ of|back to top|close)", line, re.I):
            continue

        if current_date:
            url = link_lookup.get(line, None)
            article = {
                "date": current_date,
                "headline": line,
                "url": url
            }
            articles.append(article)
            print(f"[DEBUG] Added article: {article}")

    return articles

# ----------------------------
# Page loading
# ----------------------------
def load_page(url: str) -> str:
    """Load fully rendered page HTML using Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()
        return html

def get_title_and_icon(url: str, timeout: int = 10):
    headers = {"User-Agent": "Mozilla/5.0"}

    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    raw_title = soup.title.string.strip() if soup.title else None
    safe_title = filename_safe(raw_title)

    # favicon logic unchanged
    icon_url = None
    icon_rels = {"icon", "shortcut icon", "apple-touch-icon"}

    for link in soup.find_all("link", rel=True):
        rels = {r.lower() for r in link.get("rel", [])}
        if rels & icon_rels and link.get("href"):
            icon_url = urljoin(url, link["href"])
            break

    if not icon_url:
        icon_url = urljoin(url, "/favicon.ico")

    return {
        "title": raw_title,
        "filename": safe_title,
        "icon": icon_url,
    }

# helper function to normalize filenames
def filename_safe(
    text: str,
    replacement: str = "_",
    max_length: int = 255,
) -> str:
    if not text:
        return "untitled"

    # Normalize unicode → ASCII
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Remove invalid filename characters
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", text)

    # Replace whitespace with replacement
    text = re.sub(r"\s+", replacement, text)

    # Collapse multiple replacements
    text = re.sub(rf"{re.escape(replacement)}+", replacement, text)

    # Trim leading/trailing separators and dots
    text = text.strip(f"{replacement}.")

    # Windows reserved names check
    if text.upper() in WINDOWS_RESERVED:
        text = f"{text}_file"

    # Enforce length
    if len(text) > max_length:
        text = text[:max_length].rstrip(replacement)

    return text or "untitled"

# helper function to get existing hash from JSON
def get_existing_hash(
    safe_filename: str,
    data_dir: str | Path = "data",
) -> Optional[str]:
    data_dir = Path(data_dir)
    json_path = data_dir / f"{safe_filename}.json"

    if not json_path.exists():
        return None

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    return data.get("hash")

# ----------------------------
# Main execution
# ----------------------------
if __name__ == "__main__":
    URL = "https://www.nyc.gov/mayors-office/news/?"
    # Extract HTML title
    # Extract Icon
    html = load_page(URL)
    html_info = get_title_and_icon(URL)
    html_title = html_info["title"]
    # Check data folder for HTML title.json
    # If exists, grab previous hash
    existing_hash = get_existing_hash(html_title)

    # Crop press region for article extraction
    cropped_html = extract_press_region(html)
    html_hash = hash(cropped_html)

    if existing_hash:
        print(f"Found existing file, hash = {existing_hash}")
        if existing_hash == str(html_hash):
            print("Hashes match, skipping extraction")
            exit(0)
    else:
        print("No existing file found. Contuinuing with extraction.")
        # Otherwise extract structured articles (line-based mapping)
        article_list = extract_articles_from_lines(cropped_html, BASE := "https://www.nyc.gov")

        # Construct output JSON
        output = {
            "url": URL,
            "icon": html_info["icon"],
            "title": html_title,
            "hash": str(html_hash),
            "articles": article_list,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Save to data/{filename}.json
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        output_path = data_dir / f"{html_info['filename']}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)