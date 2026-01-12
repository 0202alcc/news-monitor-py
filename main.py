import time
from pageloader import PageLoader
from metadata import MetadataExtractor
from HTML_processor import HTMLProcessor
from article_extraction import ArticleExtractor
from data_storage import DataStore
from hashing import compute_articles_hash


class PressScraper:
    def __init__(self, base_url: str):
        self.loader = PageLoader()
        self.meta = MetadataExtractor()
        self.processor = HTMLProcessor()
        self.articles = ArticleExtractor()
        self.store = DataStore()
        self.base_url = base_url

    def run(self, url: str):
        html = self.loader.load(url)
        meta = self.meta.extract(url)

        cropped = self.processor.extract_press_region(html)
        articles = self.articles.extract(cropped, self.base_url)

        # Load previous state
        old_articles = self.store.load_existing_articles(meta["filename"])

        def key(a): return (a["date"], a["headline"], a["url"])

        old_keys = {key(a) for a in old_articles}

        # Detect new articles
        new_articles = [a for a in articles if key(a) not in old_keys]

        if not new_articles:
            print("No new articles — exiting.")
            return

        print(f"Found {len(new_articles)} new articles.")

        # Merge
        merged_articles = old_articles + new_articles

        # Hash merged state
        content_hash = compute_articles_hash(merged_articles)

        # Save
        self.store.save(meta["filename"], {
            "url": url,
            "icon": meta["icon"],
            "title": meta["title"],
            "hash": content_hash,
            "articles": merged_articles,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })



if __name__ == "__main__":
    scraper = PressScraper(base_url="https://www.nyc.gov")
    scraper.run("https://www.nyc.gov/mayors-office/news/?")

