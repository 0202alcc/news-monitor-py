import json
from pathlib import Path
from typing import Optional

class DataStore:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.pages_dir = self.data_dir / "pages"
        self.pages_dir.mkdir(exist_ok=True)
        self.registry_path = self.data_dir / "registry.json"

        # Initialize empty registry if it doesn't exist
        if not self.registry_path.exists():
            self.save_registry({})

    # -----------------------------
    # Existing methods (unchanged)
    # -----------------------------
    def get_existing_hash(self, filename: str) -> Optional[str]:
        path = self.pages_dir / f"{filename}.json"
        if not path.exists():
            return None

        try:
            with path.open() as f:
                return json.load(f).get("hash")
        except Exception:
            return None

    def save(self, filename: str, payload: dict):
        path = self.pages_dir / f"{filename}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load_existing_articles(self, filename: str) -> list[dict]:
        path = self.pages_dir / f"{filename}.json"
        if not path.exists():
            return []

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("articles", [])
        except (OSError, json.JSONDecodeError):
            return []

    # -----------------------------
    # Registry helpers (new)
    # -----------------------------
    def load_registry(self) -> dict:
        try:
            with self.registry_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def save_registry(self, registry: dict):
        with self.registry_path.open("w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

    def add_page(self, page_id: str, url: str, title: str, filename: str):
        registry = self.load_registry()
        registry[page_id] = {
            "url": url,
            "title": title,
            "filename": filename,
            "enabled": True,
            "last_checked": None
        }
        self.save_registry(registry)

    def disable_page(self, page_id: str):
        registry = self.load_registry()
        if page_id in registry:
            registry[page_id]["enabled"] = False
            self.save_registry(registry)

    def update_last_checked(self, page_id: str, timestamp: str):
        registry = self.load_registry()
        if page_id in registry:
            registry[page_id]["last_checked"] = timestamp
            self.save_registry(registry)
