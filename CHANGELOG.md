# Changelog — DjResource

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
