import json
from pathlib import Path
from typing import List, Dict

from .wallhaven_service import Wallpaper


class FavoritesService:
    def __init__(self):
        self.config_dir = Path.home() / ".config/wallpicker"
        self.favorites_file = self.config_dir / "favorites.json"
        self.favorites: Dict[str, dict] = {}
        self._load_favorites()

    def _load_favorites(self):
        try:
            if self.favorites_file.exists():
                with open(self.favorites_file, "r") as f:
                    self.favorites = json.load(f)
            else:
                self.favorites = {}
        except Exception as e:
            print(f"Error loading favorites: {e}")
            self.favorites = {}

    def _save_favorites(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.favorites_file, "w") as f:
                json.dump(self.favorites, f, indent=2)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def _wallpaper_to_dict(self, wallpaper: Wallpaper) -> dict:
        return {
            "id": wallpaper.id,
            "url": wallpaper.url,
            "path": wallpaper.path,
            "thumbs_large": wallpaper.thumbs_large,
            "thumbs_small": wallpaper.thumbs_small,
            "resolution": wallpaper.resolution,
            "category": wallpaper.category,
            "purity": wallpaper.purity,
            "colors": wallpaper.colors,
            "file_size": wallpaper.file_size,
        }

    def add_favorite(self, wallpaper: Wallpaper):
        self.favorites[wallpaper.id] = self._wallpaper_to_dict(wallpaper)
        self._save_favorites()

    def remove_favorite(self, wallpaper_id: str):
        if wallpaper_id in self.favorites:
            del self.favorites[wallpaper_id]
            self._save_favorites()

    def is_favorite(self, wallpaper_id: str) -> bool:
        return wallpaper_id in self.favorites

    def get_favorites(self) -> List[Wallpaper]:
        wallpapers = []
        for data in self.favorites.values():
            try:
                wallpapers.append(Wallpaper(**data))
            except Exception as e:
                print(f"Error parsing favorite: {e}")
        return wallpapers
