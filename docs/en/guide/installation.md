# Installation

## Prerequisites

- Python **3.9 or newer**
- Django **4.2 or newer**
- An existing Django project

## From PyPI

```bash
pip install djresource
```

## From source

```bash
git clone https://github.com/NockiProgramTECH/djresource.git
cd djresource
pip install -e .
```

## Configuration

Add `"djresource"` to `INSTALLED_APPS`:

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

!!! note "Why?"
    Adding it to `INSTALLED_APPS` is required so Django can find the
    default templates provided by the library
    (`djresource/templates/djresource/*.html`).

## Verify the installation

```bash
python manage.py check
```

If everything is fine, no error is displayed. You can move on to the
[Quickstart](quickstart.md).
