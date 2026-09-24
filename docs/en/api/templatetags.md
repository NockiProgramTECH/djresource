# Template tags and filters

The `djresource/templatetags/djresource_tags.py` module provides filters
for displaying dynamic fields and tags for injecting a
CRUD component into any page.

## Loading

```django
{% load djresource_tags %}
```

## Filters

### `get_attr`

Returns the value of a dynamic attribute/field of an object (name coming from
`list_display` for example). Calls callables automatically.

```django
{{ object|get_attr:field }}
```

::: djresource.templatetags.djresource_tags.get_attr

### `get_fields_display`

Returns the list of fields (human-readable label, value) of a model
instance — used by the detail view. Handles `choices` fields via
`get_<field>_display()`.

::: djresource.templatetags.djresource_tags.get_fields_display

## Component injection tags

These tags render **only** the component (list, form, detail),
with no page structure: place them in a page you have already laid out
yourself.

!!! note
    They require the context processor
    `django.template.context_processors.request`.

!!! warning "Permissions and object scope"
    Component tags use the same authentication and business-permission chain
    as full generated views. Their object lookups also use
    `scope_queryset(queryset, request)`; a tag cannot bypass an owner's
    queryset scope.

### `djresource_list`

```django
{% djresource_list "produits.resources.ProduitResource" %}
```

::: djresource.templatetags.djresource_tags.djresource_list

### `djresource_form`

Creation if `lookup` is omitted, update otherwise. `lookup` is the value of
the Resource's `lookup_field` (pk by default):

```django
{% djresource_form "produits.resources.ProduitResource" %}
{% djresource_form "produits.resources.ProduitResource" produit.slug %}
```

Options: `template=` (overrides the partial), `cle=valeur` (data
merged into the partial's context).

::: djresource.templatetags.djresource_tags.djresource_form

### `djresource_detail`

`lookup` is the value of the Resource's `lookup_field` (pk by
default):

```django
{% djresource_detail "produits.resources.ProduitResource" produit.slug %}
```

Same options as `djresource_form`.

::: djresource.templatetags.djresource_tags.djresource_detail
