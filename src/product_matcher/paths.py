from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_data_root() -> Path:
    override = os.environ.get("PRODUCT_MATCHER_DATA_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "product-matcher-desktop"
        return Path.home() / "AppData" / "Local" / "product-matcher-desktop"
    return PROJECT_ROOT


DATA_ROOT = get_data_root()
CONFIG_DIR = DATA_ROOT / "config"
DICTIONARY_DIR = CONFIG_DIR / "dictionaries"
RUNTIME_DIR = DATA_ROOT / "runtime_data"
