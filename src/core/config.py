import os
import json
import logging
from pathlib import Path

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

APP_NAME = "ProfilePull"
APPDATA_DIR = Path(os.path.expandvars(f"%APPDATA%\\{APP_NAME}"))
CONFIG_FILE = APPDATA_DIR / "config.json"

DEFAULT_CONFIG = {
    "base_dir": "",
    "low_disk_warning": True,
    "video_quality": "bestvideo+bestaudio/best",
    "resort_on_repull": True,
    "rate_limit_retry_interval": 30
}

class ConfigManager:
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self.ensure_appdata_dir()
        self.load_config()

    def ensure_appdata_dir(self):
        APPDATA_DIR.mkdir(parents=True, exist_ok=True)

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._config.update(loaded)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        else:
            self.save_config()

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value
        self.save_config()

    @property
    def base_dir(self) -> str:
        return self.get("base_dir")
        
    @base_dir.setter
    def base_dir(self, value: str):
        self.set("base_dir", value)

config_manager = ConfigManager()
