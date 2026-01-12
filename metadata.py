import requests
import unicodedata
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config import WINDOWS_RESERVED

class MetadataExtractor:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def filename_safe(self, text: str, replacement="_", max_length=255) -> str:
        if not text:
            return "untitled"

        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", text)
        text = re.sub(r"\s+", replacement, text)
        text = re.sub(rf"{re.escape(replacement)}+", replacement, text)
        text = text.strip(f"{replacement}.")

        if text.upper() in WINDOWS_RESERVED:
            text = f"{text}_file"

        return text[:max_length] or "untitled"

    def extract(self, url: str) -> dict:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=self.timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        title = soup.title.string.strip() if soup.title else None
        filename = self.filename_safe(title)

        icon = None
        for link in soup.find_all("link", rel=True):
            rels = {r.lower() for r in link.get("rel", [])}
            if rels & {"icon", "shortcut icon", "apple-touch-icon"} and link.get("href"):
                icon = urljoin(url, link["href"])
                break

        if not icon:
            icon = urljoin(url, "/favicon.ico")

        return {
            "title": title,
            "filename": filename,
            "icon": icon,
        }
