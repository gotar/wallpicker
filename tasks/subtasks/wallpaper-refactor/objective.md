# Wallpicker Refactoring

Objective: Modernize Wallpicker architecture with clean separation of concerns, proper package structure, and Python best practices while preserving all existing functionality.

Status legend: [ ] todo, [~] in-progress, [x] done

Tasks
- [ ] 01 — Modern Python packaging with pyproject.toml → `01-package-structure.md`
- [ ] 02 — Rich domain models for Wallpaper, Config, User → `02-domain-models.md`
- [ ] 03 — Refactored service layer with DI container → `03-service-layer.md`
- [ ] 04 — MVVM architecture for GTK UI → `04-ui-architecture.md`
- [ ] 05 — Consistent async/await throughout → `05-async-refactor.md`
- [ ] 06 — Custom exception hierarchy → `06-error-handling.md`
- [ ] 07 — Migration to pytest with fixtures → `07-testing-refactor.md`
- [ ] 08 — Full type hints with mypy → `08-type-safety.md`
- [ ] 09 — Structured logging setup → `09-logging.md`
- [ ] 10 — Ruff and black configuration → `10-code-quality.md`

Dependencies
- 02 depends on 01 (domain models need proper package)
- 03 depends on 02 (services depend on domain models)
- 04 depends on 03 (UI depends on refactored services)
- 05 depends on 03 (async refactor needs service layer)
- 06 depends on 02 (exceptions used in domain models)
- 07 depends on 01, 02, 03 (pytest needs proper structure)
- 08 depends on 01, 02, 03, 04 (type hints across codebase)
- 09 depends on 01, 02, 03 (logging for services)
- 10 depends on all previous (quality tools on final code)

Exit criteria
- The refactoring is complete when:
  - All services use dependency injection
  - UI follows MVVM pattern with clear separation
  - All async operations use consistent patterns
  - Custom exceptions replace generic error handling
  - Full pytest test suite passes
  - mypy reports no type errors
  - Structured logging replaces print statements
  - Ruff passes all linting checks
  - All existing functionality preserved
