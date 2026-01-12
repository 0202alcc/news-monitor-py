from bs4 import BeautifulSoup
from config import DATE_REGEX
import re

class ArticleExtractor:
    NOISE_RE = re.compile(
        r"(filter|showing \d+ of|show \d+ more|back to top|close)",
        re.I
    )

    def extract(self, html: str, base_url: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        lines = [l.strip() for l in soup.get_text("\n").splitlines() if l.strip()]

        link_map = {
            a.get_text(strip=True): a["href"]
            for a in soup.find_all("a", href=True)
        }

        articles = []
        current_date = None

        for line in lines:
            if DATE_REGEX.search(line):
                current_date = line
                continue

            # 🔴 Filter noise explicitly
            if self.NOISE_RE.search(line):
                continue

            if current_date:
                url = link_map.get(line)

                # 🔴 Require URL to qualify as an article
                if not url:
                    continue

                articles.append({
                    "date": current_date,
                    "headline": line,
                    "url": url,
                })

        return articles
