# Journal des modifications — DjResource

## [0.1.0] — 2026-09-03

### Ajouté
- Première version publique de la bibliothèque.
- Classe `Resource` : génération automatique des vues CRUD (List, Detail, Create, Update, Delete).
- Génération automatique du formulaire (`modelform_factory`) avec injection des classes CSS du thème.
- Génération automatique des routes via `.urls()`.
- 3 thèmes de templates : Bootstrap 5 (défaut), Tailwind, Plain.
- Système de surcharge des templates par template explicite ou bloc d'extension.
- `get_extra_context(view)` : injection de données métier dans toutes les vues.
- `get_permissions()` : hook de permissions.
- `get_base_queryset()` : filtre commun avec `select_related`/`prefetch_related`.
- `search_fields`, `ordering_fields`, `list_display`, `paginate_by`.
- Messages de confirmation automatiques (`django.contrib.messages`).
- Balises de template : `djresource_list`, `djresource_form`, `djresource_detail`.
- Filtres de template : `get_attr`, `get_fields_display`.
- Tests d'intégration (CRUD complet).