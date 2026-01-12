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
# Date detection
# ----------------------------
def find_date_lines(lines: List[str]) -> List[int]:
    """Return the line indices containing dates."""
    return [i for i, line in enumerate(lines) if DATE_REGEX.search(line)]

# ----------------------------
# Cropping
# ----------------------------
def crop_lines_by_dates(lines: List[str], date_indices: List[int], padding: int = 1) -> List[str]:
    """Crop lines from just before first date to just after last date."""
    if not date_indices:
        return []
    
    start = max(0, date_indices[0] - padding)
    end = min(len(lines), date_indices[-1] + padding + 1)
    
    return lines[start:end]

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
def extract_press_region(html: str) -> str:
    """
    Crop HTML to only include the press region (dense cluster of dates + headlines).
    Returns HTML string.
    """
    linear_text = linearize_html(html)
    lines = linear_text.splitlines()
    date_indices = find_date_lines(lines)
    cropped_lines = crop_lines_by_dates(lines, date_indices, padding=2)
    cleaned_lines = clean_lines(cropped_lines)

    print(f"[DEBUG] Date lines: {date_indices}")
    print(f"[DEBUG] Cropped {len(cropped_lines)} lines, cleaned {len(cleaned_lines)} lines")

    # Build a minimal HTML with only the relevant text
    soup = BeautifulSoup(html, "html.parser")
    press_html = BeautifulSoup("", "html.parser")
    
    # Use a set for fast lookup
    cleaned_set = set(cleaned_lines)

    matches = 0
    for tag in soup.find_all(["a", "p", "div", "span"], recursive=True):
        text = tag.get_text(strip=True)
        # Include tag if any cleaned line is substring of tag text
        if any(cl in text for cl in cleaned_set):
            press_html.append(tag)
            matches += 1

    print(f"[DEBUG] Tags matched in press region: {matches}")
    return str(press_html)

# ----------------------------
# Article extraction
# ----------------------------
def extract_articles(cropped_html: str) -> List[Dict]:
    """
    Parse the cropped HTML and return a list of articles with date, headline, and URL if available.
    """
    soup = BeautifulSoup(cropped_html, "html.parser")
    articles = []
    current_date = None

    for el in soup.find_all(["a", "p", "div", "span"], recursive=True):
        text = el.get_text(strip=True)
        if not text:
            continue

        # Flexible date detection
        match = DATE_REGEX.search(text)
        if match:
            current_date = match.group().strip()
            print(f"[DEBUG] Found date: {current_date}")
            continue

        # Skip lines that are just UI noise
        if re.search(r"(filter|showing \d+ of|back to top|close)", text, re.I):
            continue

        href = el.get("href")
        if href:
            # Convert relative URLs to absolute
            if href.startswith("/"):
                href = BASE_URL + href

        article = {
            "date": current_date if current_date else "",
            "headline": text,
            "url": href if href else None
        }

        if current_date:
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
    
    # Extract structured articles
    article_list = extract_articles(cropped_html)
    
    # Optional: print cropped text for debugging
    print("\n=== CROPPED PRESS REGION ===\n")
    print(BeautifulSoup(cropped_html, "html.parser").get_text("\n"))
    
    # Print structured JSON
    print("\n=== EXTRACTED ARTICLES ===\n")
    print(json.dumps(article_list, indent=2))
