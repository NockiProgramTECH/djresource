# Resource class

This is the heart of the library. A `Resource` subclass declares a Django
model + configuration attributes; the CRUD views, the form, and
the routes are generated automatically at runtime.

## Minimal example

```python
from djresource.resource import Resource
from .models import Produit

class ProduitResource(Resource):
    model = Produit
    list_display = ["nom", "prix", "stock"]
    search_fields = ["nom"]
```

## Reference

::: djresource.resource.Resource

## Security defaults

Generated resources require authentication unless `public = True` is set
explicitly. The default `fields = []` means that no model field is writable;
declare an explicit allowlist for every create/update form. The legacy
`fields = "__all__"` value is supported for compatibility but emits
`FieldsAllWarning`.

Override `scope_queryset(queryset, request)` for tenant or owner isolation.
`get_queryset(request)` applies that scope to the base queryset and is used
for list, detail, update, delete, and injected component contexts.

## Template resolution

::: djresource.resource.Resource._theme_template

## Object lookup (`lookup_field`)

::: djresource.resource.Resource.get_lookup_url
::: djresource.resource.Resource.get_lookup_value

## Component context (injection tags)

::: djresource.resource.Resource.get_list_context
::: djresource.resource.Resource.get_form_context
::: djresource.resource.Resource.get_detail_context
