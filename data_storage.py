import json
from pathlib import Path
from typing import Optional

class DataStore:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def get_existing_hash(self, filename: str) -> Optional[str]:
        path = self.data_dir / f"{filename}.json"
        if not path.exists():
            return None

        try:
            with path.open() as f:
                return json.load(f).get("hash")
        except Exception:
            return None

    def save(self, filename: str, payload: dict):
        path = self.data_dir / f"{filename}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load_existing_articles(self, filename: str) -> list[dict]:
        path = self.data_dir / f"{filename}.json"
        if not path.exists():
            return []

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("articles", [])
        except (OSError, json.JSONDecodeError):
            return []