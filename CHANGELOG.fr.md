# Journal des modifications — DjResource

## [0.2.0] — Non publiée

### Ajouté
- Authentification par défaut (`LoginRequiredMixin`), désactivation explicite avec `public = True` ; permissions aussi appliquées aux contextes injectés.
- `scope_queryset()` / `get_queryset(request)` selon la requête pour tous les accès aux objets.
- Champs modifiables explicites (liste vide par défaut) ; avertissement pour `fields = "__all__"`.
- `list_filter` : filtres booléens/choix validés, combinés à la recherche et au tri.
- `readonly_fields`, `lookup_field` / convertisseur d’URL personnalisables, `widget_classes` / `widget_attrs` par champ.
- Hooks métier : `clean`, `before_save`, `after_save`, `before_delete`, `after_delete`.
- `inlines` optionnels : validation, sauvegarde atomique parent/enfants, rendu dans les formulaires fournis.
- Balises de données brutes et méthodes de contexte pour listes, formulaires et détails.
- Formulaires avec fichiers et affichage des relations.
- Signaux Django natifs `resource_pre_save`, `resource_post_save`, `resource_post_delete`.
- Réponses partielles HTMX optionnelles (confirmation de suppression incluse), avec `Vary: HX-Request`.
- Export CSV des résultats isolés/recherchés/filtrés/triés, sans pagination ; protection contre les formules de tableur.
- Actions groupées transactionnelles optionnelles, permissions et contrôles de sélection dans les trois thèmes.
- Bridge `as_admin_class()` partageant liste/recherche/filtres avec l’admin.
- Bridge DRF optionnel et chargé à la demande (`as_viewset()`, `djresource[api]`) : CRUD isolé, adaptateur de permissions, hooks/signaux, recherche/filtres/tri et pagination.
- CI Django 5.2/6.0 avec versions Python compatibles ; tests DRF optionnels dédiés.

### Corrigé
- Branchement des hooks sauvegarde/suppression et des inlines aux vues HTTP générées.
- Conservation des erreurs inline, absence de sauvegarde après refus de validation, annulation du parent en cas d’échec inline.
- Aucun faux message de succès après un refus de suppression.

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
