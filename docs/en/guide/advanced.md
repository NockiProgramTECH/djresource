# Advanced features

## Permissions

By default, generated views require authentication. Set `public = True`
to make a resource public explicitly. Additional permission mixins can be
returned by overriding `get_permissions()`.

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class ProduitResource(Resource):
    model = Produit

    def get_permissions(self):
        return [
            LoginRequiredMixin,
            # PermissionRequiredMixin (nécessite permission_required en attribut)
        ]
```

The same permission chain is applied to injected components, including
`UserPassesTestMixin` and custom business permission mixins.

!!! important "Partials are protected too"
    Permissions apply to full pages **AND** to components
    injected by the `{% djresource_list %}` tags etc.: before
    building a partial's context, the library simulates the
    `dispatch()` of the relevant view and raises `PermissionDenied` if the
    request is not authorized. An anonymous visitor therefore cannot read
    the data of a protected Resource by injecting it into a public
    page.

!!! tip "MRO order"
    Mixins are placed **before** the generic Django view in the `bases` tuple.
    Any method called by Django (`dispatch`, `get_queryset`,
    `get_context_data`, `form_valid`…) therefore goes through your mixins first.

## Query optimization

Avoid the N+1 problem on relations:

```python
class CommandeResource(Resource):
    model = Commande
    select_related = ["client", "livreur"]
    prefetch_related = ["articles"]
```

- `select_related`: ForeignKey / OneToOne (SQL join).
- `prefetch_related`: ManyToMany and reverse relations.

## Common filter on the queryset

Override `scope_queryset()` to isolate objects for the current request.
It is applied to **all** views (List, Detail, Update, Delete) and injected
contexts:

```python
class ProduitResource(Resource):
    model = Produit

    def scope_queryset(self, queryset, request):
        return queryset.filter(owner=request.user)
```

`get_base_queryset()` remains the hook for the model-wide base queryset;
`get_queryset(request)` returns the fully scoped queryset.

## Change the URL lookup field

By default, detail, update and delete URLs identify an
object by its pk (`<int:pk>`). With the `lookup_field` attribute, you can
use any other **unique field** of the model — typically a
`slug`, a `uid`, a reference…:

```python
class ArticleResource(Resource):
    model = Article
    lookup_field = "slug"    # au lieu du pk
```

The generated URLs then become:

- `/articles/riz-local/` (detail),
- `/articles/riz-local/modifier/` (update),
- `/articles/riz-local/supprimer/` (delete).

The library picks the right Django URL converter based on the field
type (`Resource.get_lookup_url()`):

| Field | Converter | Example |
|---|---|---|
| `IntegerField` / `AutoField` (pk) | `<int:nom>` | `/produits/42/` |
| `SlugField` | `<slug:nom>` | `/articles/riz-local/` |
| `UUIDField` | `<uuid:nom>` | `/commandes/550e8400-…/` |
| any other field | `<str:nom>` | `/codes/REF-2026/` |

!!! warning "Unique field required"
    The field must be **unique**: object resolution
    (`ResourceLookupMixin.get_object`) uses
    `get_object_or_404(queryset, lookup_field=valeur)`. Two objects sharing
    the same value would raise a `MultipleObjectsReturned` error.

Templates adapt automatically (list, detail and
form links use the value of `resource.lookup_field`, never a hardcoded `pk`).
See `ArticleResource` and `ArticleSlugLookupTests` in the test
suite (`tests/`) for a complete example.

## Inject a CRUD component into any page

The `djresource_list`, `djresource_form` and `djresource_detail` tags
let you display a CRUD component **inside a page you have already
coded**, with your own structure around it. They render **only** the
component (no `<html>`, no navbar).

```html
{% load djresource_tags %}

<h1>Mon tableau de bord</h1>
{% djresource_list "produits.resources.ProduitResource" %}
```

```html
{% load djresource_tags %}
{% djresource_form "produits.resources.ProduitResource" %}              {# création #}
{% djresource_form "produits.resources.ProduitResource" produit.slug %} {# modification #}
```

```html
{% load djresource_tags %}
{% djresource_detail "produits.resources.ProduitResource" produit.slug %}
```

The 2nd argument of the `djresource_form` / `djresource_detail` tags is the
value of the Resource's `lookup_field` field: `produit.pk` (by default),
`produit.slug`, `produit.uid`… depending on your configuration.

### Tag options

- **`template=`**: overrides the partial template used for rendering
  (by default, the Resource theme's partial).
  ```html
  {% djresource_list "..." template="monapp/_tableau.html" %}
  ```
- **`cle=valeur`**: extra data merged into the partial's context,
  available in the template like any other variable.
  ```html
  {% djresource_list "..." titre="Promos du jour" %}
  ```

### Injected component content

Partials (`*_partial.html`, available per theme) contain neither `<html>`,
nor navbar: only the component. Their context is the same as the
corresponding full-page view: `resource`, `verbose_name`, the named
URLs (`url_list`, `url_create`, `url_update`, `url_delete`),
`object_list`, `page_obj`, `list_display`, and the
`get_extra_context()` data. Partials expose the same extension blocks
as full-page templates: `list_top`, `list_bottom`, `form_top`,
`form_bottom`, `detail_extra`.

!!! note "Context"
    These tags require the
    `django.template.context_processors.request` context processor (enabled by default).

## Custom success messages

Messages use `django.contrib.messages`. Customize them:

```python
class ProduitResource(Resource):
    model = Produit
    success_message_create = "Le produit %(name)s a bien été créé."
    success_message_update = "Le produit %(name)s a bien été modifié."
    success_message_delete = "%(name)s a bien été supprimé."
```

`%(name)s` is replaced by the model's `verbose_name` (create/update) or
by `str(objet)` (delete).

## Available context variables

`ResourceContextMixin` injects into **all** templates:

| Variable | Content |
|---|---|
| `resource` | The current resource instance |
| `verbose_name` / `verbose_name_plural` | Model labels |
| `url_list` / `url_create` / `url_detail` / `url_update` / `url_delete` | Route names (for `{% url %}`) |
| `list_display` | List columns (list view) |
| `search_query` / `search_enabled` | Search state (list view) |
| `current_sort` / `current_dir` | Sort state (list view) |

!!! warning "Dynamic route names"
    The default templates never call `{% url 'produit_list' %}`:
    they use the `url_list` variables, etc., because the exact
    resource name is only known when included in `urls.py`.
