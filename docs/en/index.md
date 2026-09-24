# DjResource

![Logo DjResource](assets/logo.svg){ align="right" width="140" }

**DjResource** is a library for **Django** that automatically generates the CRUD views (Create, Read, Update, Delete), the form, and the routes of a model — from a single `Resource` class.

No more repetitive code: views, forms, and templates are created for you, while remaining 100% overridable.

## Why DjResource?

In a typical Django project, setting up the CRUD for a model requires writing by hand:

- 5 views (List, Create, Read, Update, Delete),
- 1 form (`ModelForm`),
- 4 to 5 templates,
- the corresponding routes.

This is repetitive, time-consuming, and identical from one model to the next. **DjResource replaces all of this with a class of just a few lines:**

```python
class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "prix", "stock"]
    list_display = ["nom", "prix", "stock"]
    search_fields = ["nom"]
    ordering_fields = ["nom", "prix"]
```

And the equivalent of a single line in `urls.py` to wire up the 5 routes.

## Features

| Feature | Description |
|---|---|
| Full CRUD | List, Create, Detail, Update, Delete generated automatically |
| Auto form | `ModelForm` created from the model and `fields` |
| Named routes | `.urls()` ready to include, `<model>_list`, `<model>_create`… names |
| Search | Text search bar over `search_fields` (`?q=`) |
| Filters | Dropdown lists over `list_filter` (`?champ=valeur`, combinable with `?q=`) |
| Sorting | Sortable columns (`?sort=` + `?dir=`) restricted to `ordering_fields` |
| Pagination | Configurable via `paginate_by` (default: 20) |
| Custom lookup | Detail/update/delete URLs via any field (`lookup_field`: pk, slug, uid…) |
| 3 themes | Bootstrap 5 (default), Tailwind, Plain |
| Success messages | Via `django.contrib.messages` |
| N+1 optimization | Automatic `select_related` / `prefetch_related` |
| Customization | Overridable templates, business context, permissions |
| Component injection | `{% djresource_list %}` etc. tags in any page |

## Get started securely

```bash
pip install djresource
```

```python
INSTALLED_APPS = [..., "djresource"]
```

```python
# produits/resources.py
from djresource.resource import Resource
from .models import Produit

class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "prix", "stock"]
    list_display = ["nom", "prix", "stock"]
    public = False

    def scope_queryset(self, queryset, request):
        return queryset.filter(owner=request.user)
```

```python
# urls.py
from django.urls import include, path
from produits.resources import ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
]
```

!!! warning "Security defaults"
    Generated views require authentication, `fields` is a write allowlist,
    and object access must be scoped with `scope_queryset()`. Set
    `public = True` only for intentionally public data.

See the complete [tutorial from zero](guide/quickstart.md) before wiring a
resource into a production project.

## Documentation

- **Guide**: [Installation](guide/installation.md) → [Quickstart](guide/quickstart.md) → [Themes](guide/themes.md) → [Customization](guide/customization.md) → [Advanced features](guide/advanced.md)
- **API reference**: [Resource class](api/resource.md), [Mixins](api/mixins.md), [Tags and filters](api/templatetags.md)
- [Contributing](contributing.md) · [Changelog](changelog.md)

## License

Distributed under the [MIT license](https://github.com/NockiProgramTECH/djresource/blob/main/LICENSE).
