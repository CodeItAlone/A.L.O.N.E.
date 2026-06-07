import os
import yaml
from core.human_memory import database

class PreferenceService:
    KEY_CATEGORIES = {
        # Development preferences
        "project_path": "development",
        "ide": "development",
        "editor": "development",
        "compiler": "development",
        "programming_language": "development",
        
        # Communication preferences
        "user_name": "communication",
        "assistant_name": "communication",
        "tone": "communication",
        "greeting": "communication",
        
        # Assistant configuration preferences
        "model": "assistant",
        "voice_rate": "assistant",
        "voice_volume": "assistant",
        "voice_index": "assistant",
        "threshold": "assistant",
        "openwakeword_threshold": "assistant",
        
        # Productivity preferences
        "frequent_app": "productivity",
        "favorite_app": "productivity",
        "schedule": "productivity",
    }

    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        features = self.config.get("features", {})
        self.use_structured = features.get("use_structured_preferences", True)
        
        # Track if migration has run in this session
        self._migration_done = False
        
        # Run migration if Structured Preferences is enabled
        if self.use_structured:
            self.migrate_from_chromadb()

    def _load_config(self, path=None):
        if path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base_dir, "config.yaml")
        if not os.path.exists(path):
            if os.path.exists("config.yaml"):
                path = "config.yaml"
            elif os.path.exists("../config.yaml"):
                path = "../config.yaml"
            else:
                return {}
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def get_preference(self, key: str, default: str = None) -> str:
        key_clean = key.lower().strip()
        if self.use_structured:
            prefs = database.get_preferences()
            if key_clean in prefs:
                val = prefs[key_clean]["value"]
                print(f"[Preference Retrieved] key='{key_clean}', value='{val}'")
                return val
            
            # Fallback to ChromaDB legacy storage to locate legacy preference value
            try:
                from core import memory
                legacy_val = memory.get_preference_legacy(key)
                if legacy_val is not None:
                    # Store it back to structured SQLite storage for the future
                    self.save_preference(key, legacy_val)
                    print(f"[Preference Retrieved] key='{key_clean}', value='{legacy_val}'")
                    return legacy_val
            except Exception:
                pass
            return default
        else:
            try:
                from core import memory
                val = memory.get_preference_legacy(key)
                if val is not None:
                    print(f"[Preference Retrieved] key='{key_clean}', value='{val}'")
                    return val
            except Exception:
                pass
            return default

    def save_preference(self, key: str, value: str, category: str = None):
        key_clean = key.lower().strip()
        
        # Log when saving starts
        # If it already exists, it is an update
        exists = False
        if self.use_structured:
            prefs = database.get_preferences()
            exists = key_clean in prefs
        else:
            try:
                from core import memory
                exists = memory.get_preference_legacy(key) is not None
            except Exception:
                pass
                
        if self.use_structured:
            if not category or category == "general":
                category = self.KEY_CATEGORIES.get(key_clean, "general")
            database.set_preference(key_clean, value, category)
        else:
            try:
                from core import memory
                memory.save_preference_legacy(key, value)
            except Exception:
                pass
                
        # Perform verification immediately
        verified_val = self.get_preference(key)
        if verified_val == value:
            print("[Preference Validation Passed]")
            if exists:
                print(f"[Preference Updated] key='{key_clean}', value='{value}'")
            else:
                print(f"[Preference Saved] key='{key_clean}', value='{value}'")
        else:
            print("[Preference Validation Failed]")
            print(f"[ERROR] Failed to save/update preference key='{key_clean}' with value='{value}'. Got '{verified_val}'.")

    def delete_preference(self, key: str):
        key_clean = key.lower().strip()
        if self.use_structured:
            database.delete_preference(key_clean)
        else:
            try:
                from core import memory
                memory.delete_preference_legacy(key_clean)
            except Exception:
                pass

    def get_preferences_by_category(self, category: str) -> dict:
        if self.use_structured:
            prefs = database.get_preferences(category=category)
            return {k: v["value"] for k, v in prefs.items()}
        return {}

    def get_all_preferences(self) -> dict:
        if self.use_structured:
            prefs = database.get_preferences()
            return {k: v["value"] for k, v in prefs.items()}
        else:
            try:
                from core import memory
                if memory.pref_col:
                    data = memory.pref_col.get()
                    if data and data["ids"]:
                        return {meta["key"]: doc for doc, meta in zip(data.get("documents") or [], data.get("metadatas") or []) if meta and "key" in meta}
            except Exception:
                pass
            return {}

    def get_formatted_context(self) -> str:
        """Formats active structured preferences by category for dynamic system prompt inclusion."""
        if not self.use_structured:
            prefs = self.get_all_preferences()
            if not prefs:
                return ""
            lines = [f"  * {k}: {v}" for k, v in prefs.items()]
            return "=== USER PREFERENCES ===\n" + "\n".join(lines) + "\n========================"

        categories = ["development", "communication", "assistant", "productivity", "general"]
        formatted_blocks = []
        
        for cat in categories:
            prefs = self.get_preferences_by_category(cat)
            if prefs:
                lines = [f"  * {k}: {v}" for k, v in sorted(prefs.items())]
                formatted_blocks.append(f"[{cat.title()} Preferences]:\n" + "\n".join(lines))
        
        if not formatted_blocks:
            return ""
            
        return "=== USER PREFERENCES ===\n" + "\n\n".join(formatted_blocks) + "\n========================"

    def migrate_from_chromadb(self):
        """Copies all legacy ChromaDB preferences safely to Structured SQLite Database."""
        if self._migration_done:
            return
        self._migration_done = True
        try:
            from core import memory
            if memory.pref_col is None:
                return
            data = memory.pref_col.get()
            if not data or not data["ids"]:
                return
            
            sqlite_prefs = database.get_preferences()
            for doc, meta in zip(data.get("documents") or [], data.get("metadatas") or []):
                if not meta or "key" not in meta:
                    continue
                key = meta["key"]
                key_clean = key.lower().strip()
                # If preference is not yet stored in structured SQLite table, sync it
                if key_clean not in sqlite_prefs:
                    category = self.KEY_CATEGORIES.get(key_clean, "general")
                    database.set_preference(key_clean, doc, category)
                    print(f"[PreferenceService] Dynamic migration complete: synced '{key_clean}' to SQLite.")
        except Exception as e:
            # Shield main startup from any database / import migration exceptions
            print(f"[PreferenceService Warning] Migration failed: {e}")

# Global preference service instance
preference_service = PreferenceService()
