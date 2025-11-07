import yaml
from pathlib import Path
from typing import Dict


class ConfigLoader:
    """Loads configuration files"""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader

        Args:
            config_dir: Directory containing config files
        """
        self.config_dir = Path(config_dir)

    def load_sources(self) -> Dict:
        """Load news sources configuration"""
        return self._load_yaml("sources.yaml")

    def load_platforms(self) -> Dict:
        """Load platform configuration"""
        return self._load_yaml("platforms.yaml")

    def _load_yaml(self, filename: str) -> Dict:
        """Load a YAML configuration file"""
        filepath = self.config_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, "r") as f:
            return yaml.safe_load(f)
