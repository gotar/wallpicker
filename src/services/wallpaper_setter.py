import asyncio
import logging
import os
import subprocess
from pathlib import Path

from core.asyncio_integration import get_event_loop


class WallpaperSetter:
    def __init__(self):
        self.cache_dir = Path.home() / ".cache" / "wallpaper"
        self.symlink_path = Path.home() / ".config" / "omarchy" / "current" / "background"
        self.original_path_file = Path.home() / ".cache" / "wallpaper" / "original_path"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.symlink_path.parent.mkdir(parents=True, exist_ok=True)

    def set_wallpaper(self, image_path: str) -> bool:
        """Set wallpaper synchronously, using the global event loop."""
        try:
            loop = get_event_loop()
            future = asyncio.run_coroutine_threadsafe(self.set_wallpaper_async(image_path), loop)
            # Use timeout to avoid blocking forever
            return future.result(timeout=30)
        except RuntimeError:
            # Event loop not set up, run synchronously
            return asyncio.run(self.set_wallpaper_async(image_path))
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to set wallpaper: {e}", exc_info=True)
            return False

    async def set_wallpaper_async(self, image_path: str) -> bool:
        path = Path(image_path)
        if not path.exists():
            return False

        try:
            await self._ensure_daemon_running()
            self._update_symlink(path)
            self._save_original_path(path)
            await self._apply_wallpaper(path)
            await asyncio.to_thread(self._cleanup_old_wallpapers)
            return True
        except (OSError, subprocess.SubprocessError, RuntimeError) as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to set wallpaper: {e}", exc_info=True)
            return False
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.critical(f"Unexpected error setting wallpaper: {e}", exc_info=True)
            return False

    async def _ensure_daemon_running(self):
        process = await asyncio.create_subprocess_exec(
            "pgrep",
            "-x",
            "awww-daemon",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        if process.returncode != 0:
            await asyncio.create_subprocess_exec(
                "awww-daemon",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.sleep(1)

    def _update_symlink(self, path: Path):
        if self.symlink_path.is_symlink():
            self.symlink_path.unlink()

        self.symlink_path.symlink_to(path)

    def _save_original_path(self, path: Path):
        try:
            self.original_path_file.write_text(str(path))
        except OSError:
            pass

    async def _apply_wallpaper(self, path: Path):
        process = await asyncio.create_subprocess_exec(
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
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
        except TimeoutError as e:
            process.kill()
            await process.communicate()
            raise RuntimeError("Wallpaper transition timed out") from e

        if process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(stderr_text or "Wallpaper transition failed")

    def _cleanup_old_wallpapers(self):
        wallpapers = sorted(
            self.cache_dir.glob("wallpaper_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in wallpapers[10:]:
            old.unlink(missing_ok=True)

    def get_current_wallpaper(self) -> str | None:
        # First try reading original path file (set by random_wallpaper.sh)
        if self.original_path_file.exists():
            try:
                original_path = self.original_path_file.read_text().strip()
                if original_path and Path(original_path).exists():
                    return original_path
            except OSError:
                pass

        if self.symlink_path.is_symlink():
            try:
                # Read the immediate target of the symlink without resolving recursively
                target = os.readlink(self.symlink_path)
                path = Path(target)

                # Handle relative symlinks
                if not path.is_absolute():
                    path = self.symlink_path.parent / path

                # Normalize path (handle ..) but DO NOT resolve symlinks
                # This ensures we match what LocalService sees (which doesn't resolve symlinks)
                full_path = Path(os.path.normpath(str(path)))

                if full_path.exists():
                    return str(full_path)
            except (OSError, RuntimeError) as e:
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not resolve symlink {self.symlink_path}: {e}")
        return None
