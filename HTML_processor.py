from bs4 import BeautifulSoup
import re
from config import DATE_REGEX

class HTMLProcessor:
    def linearize(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text("\n")
        return [line.strip() for line in text.splitlines() if line.strip()]

    def clean_lines(self, lines: list[str]) -> list[str]:
        return [
            l for l in lines
            if not re.search(r"(filter|showing \d+ of|back to top|close)", l, re.I)
        ]

    def extract_press_region(self, html: str, padding: int = 2) -> str:
        lines = self.clean_lines(self.linearize(html))
        date_idxs = [i for i, l in enumerate(lines) if DATE_REGEX.search(l)]

        if not date_idxs:
            return html

        start = max(0, date_idxs[0] - padding)
        end = min(len(lines), date_idxs[-1] + padding + 1)
        target_lines = set(lines[start:end])

        soup = BeautifulSoup(html, "html.parser")
        out = BeautifulSoup("", "html.parser")

        for tag in soup.find_all(["a", "p", "div", "span"]):
            if any(t in tag.get_text(strip=True) for t in target_lines):
                out.append(tag)

        return str(out)
