# 04. UI Architecture (MVVM)

meta:
  id: wallpaper-refactor-04
  feature: wallpaper-refactor
  priority: P1
  depends_on: [03]
  tags: [ui, mvvm, gtk]

objective:
- Refactor UI layer to follow MVVM pattern, separating presentation logic from business logic in the monolithic main_window.py.

deliverables:
- src/ui/view_models/ directory with ViewModels for each tab
- src/ui/views/ directory with separate view classes
- Refactored main_window.py (simplified, focuses on app lifecycle)
- Observable state management with Gio.ListStore/Gio.ListModel
- Clean separation: View (GTK widgets), ViewModel (presentation logic), Model (domain + services)

steps:
1. Create base ViewModel (src/ui/view_models/base.py):
   ```python
   from gi.repository import GObject
   from typing import Callable, Any

   class BaseViewModel(GObject.Object):
       """Base ViewModel with observable state"""

       __gtype_name__ = "BaseViewModel"

       def __init__(self):
           super().__init__()
           self._is_busy = False
           self._error_message: Optional[str] = None

       @GObject.Property(type=bool, default=False)
       def is_busy(self) -> bool:
           return self._is_busy

       @is_busy.setter
       def is_busy(self, value: bool):
           self._is_busy = value

       @GObject.Property(type=str)
       def error_message(self) -> Optional[str]:
           return self._error_message

       @error_message.setter
       def error_message(self, value: Optional[str]):
           self._error_message = value
   ```

2. Create WallhavenViewModel (src/ui/view_models/wallhaven_view_model.py):
   ```python
   from gi.repository import GObject, Gio
   from services.wallhaven_service import WallhavenService
   from domain.wallpaper import Wallpaper

   class WallhavenViewModel(BaseViewModel):
       __gtype_name__ = "WallhavenViewModel"

       def __init__(self, service: WallhavenService):
           super().__init__()
           self._service = service
           self._wallpapers = Gio.ListStore()
           self._current_page = 1
           self._total_pages = 1

       @GObject.Property(type=Gio.ListStore)
       def wallpapers(self) -> Gio.ListStore:
           return self._wallpapers

       @GObject.Property(type=int)
       def current_page(self) -> int:
           return self._current_page

       @GObject.Property(type=int)
       def total_pages(self) -> int:
           return self._total_pages

       async def search(self, query: str, **filters) -> None:
           """Search wallpapers - async"""
           self.is_busy = True
           try:
               result = await self._service.search_async(query, **filters)
               self._wallpapers.remove_all()
               for wp in result:
                   self._wallpapers.append(wp)
               self._current_page = result.page
               self._total_pages = result.total_pages
           except Exception as e:
               self.error_message = str(e)
           finally:
               self.is_busy = False

       def next_page(self) -> None:
           if self.current_page < self.total_pages:
               self._current_page += 1
               # Trigger search again

       def prev_page(self) -> None:
           if self.current_page > 1:
               self._current_page -= 1
               # Trigger search again
   ```

3. Create LocalViewModel (src/ui/view_models/local_view_model.py):
   - Similar pattern for local wallpapers
   - Methods: load_wallpapers(), delete_wallpaper(), set_wallpaper()
   - Observable state: wallpapers list, current wallpaper

4. Create FavoritesViewModel (src/ui/view_models/favorites_view_model.py):
   - Similar pattern for favorites
   - Methods: load_favorites(), add_favorite(), remove_favorite()

5. Extract view components from main_window.py:
   - Create src/ui/views/wallhaven_view.py (Wallhaven tab UI)
   - Create src/ui/views/local_view.py (Local tab UI)
   - Create src/ui/views/favorites_view.py (Favorites tab UI)
   - Each view takes ViewModel as constructor argument

6. Refactor main_window.py:
   ```python
   class MainWindow(Adw.Application):
       def __init__(self, container: ServiceContainer):
           super().__init__(application_id="com.github.wallpicker")
           self.container = container

       def do_activate(self):
           if not self.window:
               # Create ViewModels with services from container
               wallhaven_vm = WallhavenViewModel(
                   self.container.get(WallhavenService)
               )
               local_vm = LocalViewModel(
                   self.container.get(LocalWallpaperService)
               )
               favorites_vm = FavoritesViewModel(
                   self.container.get(FavoritesService)
               )

               # Create window with ViewModels
               self.window = WallPickerWindow(
                   app=self,
                   wallhaven_vm=wallhaven_vm,
                   local_vm=local_vm,
                   favorites_vm=favorites_vm
               )
           self.window.present()

   class WallPickerWindow(Adw.ApplicationWindow):
       def __init__(self, app, wallhaven_vm, local_vm, favorites_vm):
           super().__init__(application=app)
           self.wallhaven_vm = wallhaven_vm
           self.local_vm = local_vm
           self.favorites_vm = favorites_vm

           # Create views with ViewModels
           wallhaven_view = WallhavenView(wallhaven_vm)
           local_view = LocalView(local_vm)
           favorites_view = FavoritesView(favorites_vm)

           # Setup UI
           self._setup_ui(wallhaven_view, local_view, favorites_view)
   ```

7. Setup bindings between Views and ViewModels:
   - Use GObject.Binding for property synchronization
   - Connect signals from View to ViewModel methods
   - Update View when ViewModel state changes

tests:
- Unit: Test ViewModel state management
- Unit: Test observable property changes
- Integration: Test View-ViewModel binding
- UI: Test user actions trigger ViewModel methods

acceptance_criteria:
- main_window.py reduced to ~200-300 lines (from 1023)
- ViewModels created for each tab (wallhaven, local, favorites)
- Views separated from ViewModels
- ViewModels use services from DI container
- Observable state with GObject properties
- No business logic in Views (only presentation)
- ViewModels have no direct GTK widget references
- UI tests work with ViewModels (can mock views)

validation:
- Commands to verify:
  ```bash
  python -m pytest tests/ui/ -v
  ```
- Run application and verify all tabs work
- Verify no direct service calls in view classes

notes:
- MVVM: Model (domain + services), View (GTK widgets), ViewModel (presentation)
- ViewModel is the bridge: holds UI state, calls services
- View observes ViewModel properties, calls ViewModel methods
- This pattern makes UI testable (ViewModels have no GTK dependencies)
- GObject properties are observable and bindable
- Async operations in ViewModels (await services)
