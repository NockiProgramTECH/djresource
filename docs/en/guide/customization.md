# Customization

A generated CRUD rarely displays **only** the model fields: you often
want computed information, a banner, an extra button.
Two complementary mechanisms exist, **without ever touching the view
code**.

## 1. Inject business data: `get_extra_context()`

Override it in your `Resource`. The result is automatically merged
into the context of **all** generated views (list, detail, form,
delete).

```python
class ProduitResource(Resource):
    model = Produit

    def get_extra_context(self, view):
        return {
            "valeur_stock_total": sum(
                p.prix * p.stock for p in Produit.objects.all()
            ),
        }
```

`view` is the current view instance: you can read `view.request`
from it (logged-in user, GET parameters…), and depending on the case `view.object`
(detail/update/delete) or `view.object_list` (list, already filtered/sorted).

## 2. Display this data: extension blocks

The default templates (in all 3 themes) expose empty Django blocks at
useful locations:

| Template | Available blocks |
|---|---|
| `list.html` | `list_header_actions` (next to the "+ Add" button), `list_top` (banner below the title), `list_bottom` (below the table) |
| `form.html` | `form_top` (before the form), `form_bottom` (after) |
| `detail.html` | `detail_extra` (after the fields table) |

Create a template **in your own application** that extends the default
template of the theme in use and fills in the desired block:

```html
{# produits/templates/produits/liste_produits.html #}
{% extends "djresource/list.html" %}
{# ou djresource/tailwind/list.html, djresource/plain/list.html #}

{% block list_top %}
<div class="alert alert-info">
    Valeur totale du stock : {{ valeur_stock_total }} FCFA
</div>
{% endblock %}
```

Then point your resource to this template:

```python
class ProduitResource(Resource):
    model = Produit
    template_list = "produits/liste_produits.html"

    def get_extra_context(self, view):
        return {
            "valeur_stock_total": sum(
                p.prix * p.stock for p in Produit.objects.all()
            ),
        }
```

## Filter the list: `list_filter`

```python
class ArticleResource(Resource):
    model = Article
    list_filter = ["actif", "etat"]   # booléen, champ à choices...
```

The list page then displays a dropdown per field
(`?actif=1`, `?etat=brouillon`…), which can be combined with the `?q=` search.
Invalid values are ignored (no filter).

## Override an entire template

If blocks are not enough, `template_list`, `template_detail`,
`template_form` and `template_delete` can point to a fully
standalone template that extends nothing from the library:

```python
class ProduitResource(Resource):
    model = Produit
    template_list = "produits/ma_liste_perso.html"
```

## Attribute summary table

| Attribute | Role |
|---|---|
| `model` | Django model (**required**) |
| `fields` | Writable form allowlist (empty by default; legacy `"__all__"` emits `FieldsAllWarning`) |
| `readonly_fields` | Fields displayed but not editable |
| `list_display` | Columns displayed in the list |
| `search_fields` | Fields covered by text search |
| `ordering_fields` | Fields on which click-to-sort is allowed |
| `list_filter` | Fields filterable via `?champ=valeur` (booleans, `choices` fields) |
| `paginate_by` | Number of objects per page (default: 20) |
| `lookup_field` | Field used in detail/update/delete URLs (`"pk"` by default, or `"slug"`, `"uid"`, etc.) |
| `select_related` / `prefetch_related` | Query optimization on relations |
| `theme` | `"bootstrap"` (default) \| `"tailwind"` \| `"plain"` \| custom theme |
| `auto_form_css` | Auto-injection of the theme's CSS classes on the form (default: `True`) |
| `template_list` / `template_detail` / `template_form` / `template_delete` | Override of a specific template (takes precedence over `theme`) |
| `get_extra_context(view)` | Injects additional business data into the context of all views |
| `public` | Explicitly opt out of default authentication |
| `get_permissions()` | Additional permission mixins |
| `scope_queryset(queryset, request)` / `get_queryset(request)` | Request-aware object isolation |
| `get_base_queryset()` | Base queryset with relation preloading |

!!! danger "Security: writing is deny-by-default"
    The default `fields = []` exposes no model fields in
    the generated form. If you later add a sensitive field to your
    model, it is not silently made editable. Always declare the explicit
    list of editable fields:

    ```python
    class ProduitResource(Resource):
        model = Produit
        fields = ["nom", "prix", "stock"]   # uniquement ces champs
    ```

    The legacy `fields = "__all__"` remains supported for compatibility and
    emits a `FieldsAllWarning`; do not use it for sensitive models.
