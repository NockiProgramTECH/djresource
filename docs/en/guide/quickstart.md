# Tutorial from zero

This tutorial creates a small, secure library application from an empty
directory. It assumes Python 3.9+ and Django 4.2+.

## 1. Create the project

```bash
mkdir my-library
cd my-library
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install Django djresource
django-admin startproject config .
python manage.py startapp books
```

Add both applications in `config/settings.py`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "djresource",
    "books",
]
```

The default Django authentication middleware and the request context
processor must remain enabled. DjResource protects generated CRUD views by
default.

## 2. Create the model

```python
# books/models.py
from django.conf import settings
from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150)
    published_year = models.PositiveIntegerField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="books",
    )
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return self.title
```

Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 3. Declare a secure Resource

Create `books/resources.py`. `fields` is an explicit **write allowlist**:
fields not listed there cannot be changed by the generated form. The
`scope_queryset()` hook prevents one user from accessing another user's
records.

```python
# books/resources.py
from djresource.resource import Resource
from .models import Book


class BookResource(Resource):
    model = Book
    fields = ["title", "author", "published_year"]
    readonly_fields = ["owner", "is_archived"]
    list_display = ["title", "author", "published_year", "is_archived"]
    search_fields = ["title", "author"]
    ordering_fields = ["title", "published_year"]

    def scope_queryset(self, queryset, request):
        return queryset.filter(owner=request.user)

    def before_save(self, instance, request, is_new):
        if is_new:
            instance.owner = request.user
```

Do not use `fields = "__all__"` for new resources. It is retained only as a
legacy compatibility mode and emits `FieldsAllWarning`.

## 4. Add the URLs

```python
# config/urls.py
from django.contrib import admin
from django.urls import include, path
from books.resources import BookResource

urlpatterns = [
    path("admin/", admin.site.urls),
    path("books/", include(BookResource().urls())),
]
```

## 5. Create a user and test the CRUD

```bash
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/books/`. An anonymous visitor is redirected to
the login page. After logging in, the generated routes are available:

| URL | Purpose |
|---|---|
| `/books/` | Scoped list with search, sorting, and pagination |
| `/books/nouveau/` | Create a book owned by the current user |
| `/books/<pk>/` | Detail, limited to the current user's books |
| `/books/<pk>/modifier/` | Update, limited to the current user's books |
| `/books/<pk>/supprimer/` | Delete, limited to the current user's books |

Create a second user and verify that the second user cannot see or modify the
first user's books. A record outside the scope returns HTTP 404, including
for detail, update, and delete.

## 6. Deliberately make a resource public

Public access is opt-in and explicit:

```python
class PublicBookCatalogResource(Resource):
    model = Book
    public = True
    fields = []
    list_display = ["title", "author"]
```

Use this only for data that is intentionally public. `public = True` does
not disable the `scope_queryset()` hook or any additional business rules you
implement.

Next, see [themes](themes.md), [customization](customization.md), and
[advanced features](advanced.md).
