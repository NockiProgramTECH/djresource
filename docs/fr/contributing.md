# Contribuer

Merci de votre intérêt pour DjResource ! Les contributions sont les
bienvenues : rapports de bugs, suggestions, corrections de documentation,
nouveaux thèmes, fonctionnalités.

## Environnement de développement

Le dépôt contient uniquement la bibliothèque (`djresource/`), sa suite de
tests autonome (`tests/` + `runtests.py`) et la documentation (`docs/`).

```bash
git clone https://github.com/NockiProgramTECH/djresource.git
cd djresource
python -m venv .venv
# Windows :
.venv\Scripts\activate
# Linux/macOS :
source .venv/bin/activate

pip install -e ".[test]"
```

## Lancer les tests

```bash
python runtests.py
```

## Structure du dépôt

```
djresource/
├── djresource/           # la bibliothèque (package installable)
│   ├── resource.py       # classe Resource (cœur)
│   ├── mixins.py         # mixins composant les vues générées
│   ├── templatetags/     # balises et filtres de template
│   ├── templates/        # les 3 thèmes (bootstrap, tailwind, plain)
│   └── static/           # CSS du thème "plain"
├── tests/                # suite de tests autonome (settings + modèles)
├── docs/                 # sources de la documentation (MkDocs)
├── pyproject.toml        # métadonnées du paquet PyPI
└── runtests.py           # lanceur de tests
```

## Règles

- Une fonctionnalité ajoutée à la bibliothèque doit être prouvée par un test
  d'intégration dans `tests/`.
- Une fonctionnalité ajoutée doit être documentée (README + docs MkDocs).
- Un bloc de template ajouté dans un thème doit être répercuté dans **les 3
  thèmes** (`djresource/templates/djresource/{list,form,detail,confirm_delete}.html`
  + les versions `tailwind/` et `plain/`) **ainsi que dans les partiels
  d'injection** (`*_partial.html`, même arborescence), sinon les templates
  custom des utilisateurs casseraient silencieusement.
- La langue du projet (docstrings, templates, README, documentation) est le
  **français**.
- Les mixins de `djresource/mixins.py` doivent rester mono-responsables et
  chaîner `super()` pour être librement combinables.

## Publier une version (mainteneurs)

1. Mettre à jour la version dans `pyproject.toml` et
   `djresource/__init__.py`.
2. Compléter `CHANGELOG.md`.
3. Créer un tag `vX.Y.Z` et le pousser : le workflow GitHub Actions
   `publish.yml` construit et publie automatiquement le paquet sur PyPI.

## Documentation locale

```bash
pip install mkdocs-material mkdocstrings[python]
mkdocs serve   # http://127.0.0.1:8000
```

La documentation est déployée automatiquement sur GitHub Pages à chaque
push sur `main` (workflow `docs.yml`).
