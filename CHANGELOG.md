# Changelog — DjResource

## [0.2.0] — 2026-09-26

### Added
- Authentication by default (`LoginRequiredMixin`), with explicit `public = True` opt-out; permissions also enforced for injected contexts.
- Request-aware `scope_queryset()` / `get_queryset(request)` across all object access paths.
- Explicit writable fields (empty default); warning for legacy `fields = "__all__"`.
- `list_filter` for validated boolean/choice filters combined with search and ordering.
- `readonly_fields`, custom `lookup_field` / URL converter, and per-field `widget_classes` / `widget_attrs`.
- Business hooks: `clean`, `before_save`, `after_save`, `before_delete`, `after_delete`.
- Optional `inlines`: validation and atomic parent/child saving, built-in form rendering.
- Raw-data template tags and context helpers for lists, forms and details.
- File upload forms and relation display support.
- Native `resource_pre_save`, `resource_post_save`, `resource_post_delete` Django signals.
- Opt-in HTMX partial responses (including delete confirmation), with `Vary: HX-Request`.
- CSV export of scoped, searched, filtered, sorted results without pagination; formula-injection protection.
- Optional transactional bulk actions, permission checks and selection controls in all three themes.
- `as_admin_class()` bridge sharing admin list/search/filter configuration.
- Lazy optional DRF bridge (`as_viewset()`, `djresource[api]`): scoped CRUD, permission adapter, hooks/signals, search/filter/order and pagination.
- CI coverage for Django 5.2/6.0 with supported Python versions; dedicated optional-DRF tests.

### Fixed
- Wire save/delete hooks and inline formsets into generated HTTP views.
- Preserve bound inline errors, do not save after a validation veto, and roll back parent writes on inline failure.
- No misleading success message when deletion is vetoed.

## [0.1.0] — 2026-09-03

### Added
- First public release of the library.
- `Resource` class: automatic generation of CRUD views (List, Detail, Create, Update, Delete).
- Automatic form generation (`modelform_factory`) with theme CSS class injection.
- Automatic route generation via `.urls()`.
- 3 template themes: Bootstrap 5 (default), Tailwind, Plain.
- Template override system via explicit template or extension block.
- `get_extra_context(view)`: business data injection into all views.
- `get_permissions()`: permissions hook.
- `get_base_queryset()`: shared filtering with `select_related`/`prefetch_related`.
- `search_fields`, `ordering_fields`, `list_display`, `paginate_by`.
- Automatic confirmation messages (`django.contrib.messages`).
- Template tags: `djresource_list`, `djresource_form`, `djresource_detail`.
- Template filters: `get_attr`, `get_fields_display`.
- Integration tests (full CRUD).
