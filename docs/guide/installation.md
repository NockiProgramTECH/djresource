# Installation

## Prérequis

- Python **3.9 ou plus récent**
- Django **4.2 ou plus récent**
- Un projet Django existant

## Depuis PyPI

```bash
pip install djresource
```

## Depuis les sources

```bash
git clone https://github.com/NockiProgramTECH/djresource.git
cd djresource
pip install -e .
```

## Configuration

Ajoutez `"djresource"` dans `INSTALLED_APPS` :

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # ...
    "djresource",
]
```

!!! note "Pourquoi ?"
    L'ajout dans `INSTALLED_APPS` est nécessaire pour que Django trouve les
    templates par défaut fournis par la bibliothèque
    (`djresource/templates/djresource/*.html`).

## Vérifier l'installation

```bash
python manage.py check
```

Si tout est en ordre, aucune erreur ne s'affiche. Vous pouvez passer au
[Démarrage rapide](quickstart.md).
