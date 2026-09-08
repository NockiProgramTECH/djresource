# Contributing

Thank you for your interest in DjResource! Contributions are
welcome: bug reports, suggestions, documentation fixes,
new themes, features.

## Development environment

The repository contains only the library (`djresource/`), its standalone
test suite (`tests/` + `runtests.py`) and the documentation (`docs/`).

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

## Running the tests

```bash
python runtests.py
```

## Repository structure

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

## Rules

- A feature added to the library must be proven by an integration test
  in `tests/`.
- An added feature must be documented (README + MkDocs docs).
- A template block added in one theme must be replicated in **all 3
  themes** (`djresource/templates/djresource/{list,form,detail,confirm_delete}.html`
  + the `tailwind/` and `plain/` versions) **as well as in the injection
  partials** (`*_partial.html`, same tree), otherwise users' custom
  templates would break silently.
- The project language (docstrings, templates, README, documentation) is
  **French**.
- Mixins in `djresource/mixins.py` must stay single-responsibility and
  chain `super()` so they can be freely combined.

## Publishing a release (maintainers)

1. Update the version in `pyproject.toml` and
   `djresource/__init__.py`.
2. Complete `CHANGELOG.md`.
3. Create a `vX.Y.Z` tag and push it: the GitHub Actions workflow
   `publish.yml` automatically builds and publishes the package on PyPI.

## Local documentation

```bash
pip install mkdocs-material mkdocstrings[python]
mkdocs serve   # http://127.0.0.1:8000
```

The documentation is automatically deployed to GitHub Pages on every
push to `main` (`docs.yml` workflow).
