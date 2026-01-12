from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import json

# ----------------------------
# Configuration
# ----------------------------
DATE_REGEX = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE
)
BASE_URL = "https://www.nyc.gov"

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
def extract_articles_from_lines(html: str) -> List[Dict]:
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
                href = BASE_URL + href
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

# ----------------------------
# Main execution
# ----------------------------
if __name__ == "__main__":
    URL = "https://www.nyc.gov/mayors-office/news/?"
    html = load_page(URL)

    # Crop press region for article extraction
    cropped_html = extract_press_region(html)

    # Extract structured articles (line-based mapping)
    article_list = extract_articles_from_lines(cropped_html)

    # Optional: print cropped text for debugging
    print("\n=== CROPPED PRESS REGION ===\n")
    print(BeautifulSoup(cropped_html, "html.parser"))

    # Print structured JSON
    print("\n=== EXTRACTED ARTICLES ===\n")
    print(json.dumps(article_list, indent=2))
