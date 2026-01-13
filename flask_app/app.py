import sys
from pathlib import Path
import json
import time
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for

# ------------------------------
# Make parent directory importable
# ------------------------------
sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_storage import DataStore
from main import PressScraper  # your Incremental/normal scraper

# ------------------------------
# Flask app setup
# ------------------------------
app = Flask(__name__)
store = DataStore()


# ------------------------------
# Helper to extract base_url from full URL
# ------------------------------
def get_base_url(full_url: str) -> str:
    parts = urlparse(full_url)
    return f"{parts.scheme}://{parts.netloc}"


# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def dashboard():
    registry = store.load_registry()

    # Load JSON for each enabled page
    pages_data = {}
    for page_id, page in registry.items():
        if page.get("enabled", True):
            json_path = store.pages_dir / f"{page['filename']}.json"
            if json_path.exists():
                try:
                    with json_path.open("r", encoding="utf-8") as f:
                        page_json = json.load(f)
                    pages_data[page_id] = page_json
                except Exception:
                    pages_data[page_id] = {"title": page["title"], "articles": []}
            else:
                pages_data[page_id] = {"title": page["title"], "articles": []}

    return render_template("index.html", pages=pages_data)


@app.route("/add", methods=["POST"])
def add_page():
    url = request.form["url"].strip()
    base_url = get_base_url(url)

    # Initialize scraper with base_url
    scraper = PressScraper(base_url=base_url)

    # Extract metadata: title, filename, icon
    meta = scraper.meta.extract(url)
    filename = meta["filename"]
    page_id = filename.lower().replace(" ", "-")

    # Add page to registry
    store.add_page(page_id, url, meta["title"], filename)

    # Run scraper to fetch articles (incremental)
    scraper.run(url)

    # Update last_checked timestamp in registry
    store.update_last_checked(page_id, time.strftime("%Y-%m-%d %H:%M:%S"))

    return redirect(url_for("dashboard"))


@app.route("/disable/<page_id>")
def disable_page(page_id):
    store.disable_page(page_id)
    return redirect(url_for("dashboard"))


# ------------------------------
# Run app
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
