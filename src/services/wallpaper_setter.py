import subprocess
from pathlib import Path


class WallpaperSetter:
    def __init__(self):
        self.cache_dir = Path.home() / ".cache" / "wallpaper"
        self.symlink_path = (
            Path.home() / ".config" / "omarchy" / "current" / "background"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.symlink_path.parent.mkdir(parents=True, exist_ok=True)

    def set_wallpaper(self, image_path: str) -> bool:
        path = Path(image_path)
        if not path.exists():
            return False

        try:
            self._ensure_daemon_running()
            self._update_symlink(path)
            self._apply_wallpaper(path)
            self._cleanup_old_wallpapers()
            return True
        except Exception:
            return False

    def _ensure_daemon_running(self):
        result = subprocess.run(["pgrep", "-x", "awww-daemon"], capture_output=True)
        if result.returncode != 0:
            subprocess.Popen(
                ["awww-daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            import time

            time.sleep(1)

    def _update_symlink(self, path: Path):
        if self.symlink_path.is_symlink():
            self.symlink_path.unlink()

        self.symlink_path.symlink_to(path)

    def _apply_wallpaper(self, path: Path):
        subprocess.run(
            [
                "awww",
                "img",
                "--transition-type",
                "random",
                "--transition-fps",
                "60",
                "--transition-duration",
                "3",
                "--transition-bezier",
                ".43,1.19,1,.4",
                str(path),
            ],
            check=True,
        )

    def _cleanup_old_wallpapers(self):
        wallpapers = sorted(
            self.cache_dir.glob("wallpaper_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in wallpapers[10:]:
            old.unlink(missing_ok=True)

    def get_current_wallpaper(self) -> str | None:
        if self.symlink_path.is_symlink():
            try:
                target = self.symlink_path.resolve()
                if target.exists():
                    return str(target)
            except Exception:
                pass
        return None
