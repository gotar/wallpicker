# SERVICES

**Type:** Business logic layer

## OVERVIEW
All core business logic for wallpaper fetching, caching, favorites, and wallpaper setting.

## WHERE TO LOOK
| Task | File |
|------|------|
| Wallhaven API | wallhaven_service.py |
| Local files | local_service.py |
| Thumbnail cache | thumbnail_cache.py |
| Config | config_service.py |
| Favorites DB | favorites_service.py |
| Wallpaper setter | wallpaper_setter.py |

## CONVENTIONS

### GObject Classes
All wallpaper objects inherit from GObject with `__gtype_name__`:
```python
class Wallpaper(GObject.Object):
    __gtype_name__ = "Wallpaper"
    # properties via GObject.Property()
```

### Async HTTP
Use `aiohttp` for async requests (wallhaven_service.py). Rate limit to 45 req/min.

### Fuzzy Search
Use `rapidfuzz.process.extract()` for search (wallhaven categories, local files, favorites).

### Storage Locations
- Config: `~/.config/wallpicker/config.json`
- Favorites: `~/.config/wallpicker/favorites.json`
- Thumbnails: `~/.cache/wallpicker/thumbnails/`

### File Operations
- Delete: `send2trash.send2trash()` (not os.unlink)
- Scan: `os.walk()` for recursive directory traversal
- Supported extensions: `.jpg,.jpeg,.png,.webp,.bmp,.gif`

## ANTI-PATTERNS
- Do NOT use os.unlink for deletion (use send2trash)
- Do NOT cache indefinitely (7-day expiry for thumbnails)
- Do NOT fetch thumbnails synchronously (use threads)

## PATTERNS

### Wallpaper Object
```python
{
    "id": str,
    "url": str,
    "path": str,      # local only
    "category": str,  # "wallhaven" or "local"
    "thumbnail_url": str,
    "source": str,     # "wallhaven" or "local"
    "is_favorite": bool
}
```

### Thumbnail Cache
- Filename: MD5 hash of URL
- Cleanup: Delete expired (>7 days) or oldest if >500MB
- Format: Gdk.Texture for GTK widgets
