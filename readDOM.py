from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from typing import List, Dict

# ----------------------------
# Configuration
# ----------------------------
DATE_REGEX = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE
)

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
# Extraction pipeline
# ----------------------------
def extract_press_region(html: str) -> List[str]:
    """Return a cleaned list of lines containing press articles."""
    linear_text = linearize_html(html)
    lines = linear_text.splitlines()
    date_indices = find_date_lines(lines)
    cropped = crop_lines_by_dates(lines, date_indices, padding=1)
    cleaned = clean_lines(cropped)
    return cleaned
def extract_articles(html: str) -> List[dict]:
    """
    Parse the HTML and return a list of articles with date, headline, and URL.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    articles = []
    current_date = None
    
    for el in soup.find_all(["a", "p", "div", "span"], recursive=True):
        text = el.get_text(strip=True)
        if not text:
            continue
        
        # More flexible date detection
        match = DATE_REGEX.search(text)
        if match:
            current_date = match.group().strip()
            continue
        
        url = el.get("href")
        if url and current_date:
            # Convert relative URLs to absolute
            if url.startswith("/"):
                url = "https://www.nyc.gov" + url
            articles.append({
                "date": current_date,
                "headline": text,
                "url": url
            })
    
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
    
    # Optional: get the cleaned press region for debugging
    press_lines = extract_press_region(html)
    print("\n".join(press_lines))
    
    # Extract structured articles
    article_list = extract_articles(html)
    
    import json
    print(json.dumps(article_list, indent=2))
