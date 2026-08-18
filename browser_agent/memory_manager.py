import json
import os
from typing import Dict, Any, Optional

class MemoryManager:
    """Manages persistent user preferences with explicit consent."""

    MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "user_preferences.json")

    @classmethod
    def get_preference(cls, domain_or_key: str) -> Optional[Any]:
        """Retrieves stored preference if present."""
        prefs = cls._load_preferences()
        return prefs.get(domain_or_key)

    @classmethod
    def set_preference(cls, key: str, value: Any):
        """Saves user preference."""
        prefs = cls._load_preferences()
        prefs[key] = value
        cls._save_preferences(prefs)
        print(f"[MemoryManager] Saved user preference: {key} = {value}")

    @classmethod
    def _load_preferences(cls) -> Dict[str, Any]:
        if os.path.exists(cls.MEMORY_FILE):
            try:
                with open(cls.MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_preferences(cls, prefs: Dict[str, Any]):
        try:
            with open(cls.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            print(f"[MemoryManager Error] Failed to save preferences: {e}")
