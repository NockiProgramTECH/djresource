"""
djresource.templatetags.djresource_tags
========================================

Library template filters and tags.

Two families of tags:

1. `djresource_list` / `djresource_form` / `djresource_detail`: render a
   ready-made HTML component (chosen theme) directly in your page.

2. `djresource_list_data` / `djresource_form_data` / `djresource_detail_data`:
   render NO HTML at all — they return raw data via
   `{% ... as variable %}`, for fully free-form display.

SECURITY: `resource_path` must ALWAYS be a string hardcoded in your
template, never a value built from user data (GET/POST/session) — see
the `_resolve_resource` docstring.
"""
from django import template
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

register = template.Library()


# ---------------------------------------------------------------------
# Filters (dynamic field display, including relations)
# ---------------------------------------------------------------------
def _is_related_manager(value):
    """Detects a relation manager (ManyToMany, or reverse ForeignKey)."""
    return hasattr(value, "all") and callable(getattr(value, "all", None))


@register.filter(name="get_attr")
def get_attr(obj, attr_name):
    """
    Returns the value of a dynamic attribute/field of an object, ready to
    display — including for a relation:
    - ForeignKey / OneToOneField: displays str(related object) (normal
      Django behavior, nothing special to do here).
    - ManyToManyField or reverse relation (FK from another model):
      displays the list of related objects, comma-separated.

    Usage in a template: {{ object|get_attr:field }}
    where `field` is a string (e.g. "nom", "categorie", "tags") coming
    from `list_display`.
    """
    value = getattr(obj, attr_name, "")
    if _is_related_manager(value):
        return ", ".join(str(item) for item in value.all()) or "—"
    if callable(value):
        value = value()
    return value


@register.filter(name="get_fields_display")
def get_fields_display(obj):
    """
    Returns the list of fields (readable label, value) of a model
    instance, used by the detail template to display all fields without
    knowing their names in advance.

    Covers:
    - concrete fields (including ForeignKey/OneToOneField, automatically
      displayed via their __str__),
    - fields with choices (`choices=...`), displayed via
      get_<field>_display(),
    - ManyToManyField fields (absent from `_meta.fields` in Django, so
      handled separately), displayed as a comma-separated list.
    """
    result = []
    for f in obj._meta.fields:
        value = getattr(obj, f.name)
        display_method_name = f"get_{f.name}_display"
        if hasattr(obj, display_method_name):
            value = getattr(obj, display_method_name)()
        result.append({"label": f.verbose_name, "value": value})

    for f in obj._meta.many_to_many:
        related_objects = getattr(obj, f.name).all()
        value = ", ".join(str(item) for item in related_objects) if related_objects else "—"
        result.append({"label": f.verbose_name, "value": value})

    return result


# ---------------------------------------------------------------------
# Secure resolution of a Resource from a Python path
# ---------------------------------------------------------------------
def _resolve_resource(resource_path):
    """
    Imports and instantiates a Resource from its full Python path.

    SECURITY: `resource_path` must always be a string hardcoded in your
    template (e.g. "produits.resources.ProduitResource"), never a value
    built from user data — a user-controlled path would allow importing
    and instantiating any Python class accessible in the project. A
    check (`issubclass(..., Resource)`) prevents using a class that
    isn't a Resource, but does not protect against a malicious dynamic
    path.
    """
    from ..resource import Resource  # deferred import: avoids a circular import (goes back to the parent djresource package, NOT djresource.templatetags)

    try:
        resource_class = import_string(resource_path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"djresource: unable to import '{resource_path}'. "
            "Check the path (format 'module.submodule.ClassName')."
        ) from exc

    if not (isinstance(resource_class, type) and issubclass(resource_class, Resource)):
        raise ImproperlyConfigured(
            f"djresource: '{resource_path}' is not a subclass of "
            "djresource.resource.Resource."
        )
    return resource_class()


# ---------------------------------------------------------------------
# "Rendered component" tags (ready-made HTML, chosen theme)
# ---------------------------------------------------------------------
@register.simple_tag(takes_context=True)
def djresource_list(context, resource_path):
    """
    Injects the fully rendered "list" component (table, chosen theme)
    into the current template.

    Usage:
        {% load djresource_tags %}
        {% djresource_list "produits.resources.ProduitResource" %}
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    list_context = resource.get_list_context(request)
    template_name = resource._theme_template("list_partial", None)
    return mark_safe(render_to_string(template_name, list_context, request=request))


@register.simple_tag(takes_context=True)
def djresource_form(context, resource_path, lookup=None):
    """
    Injects the fully rendered "form" component (create if `lookup` is
    omitted, update otherwise) into the current template.

    `lookup` is the value of the Resource's `lookup_field` ("pk" by
    default, so `produit.pk` in the common case — or `produit.slug` if
    the Resource defines `lookup_field = "slug"`, etc.)

    Usage:
        {% djresource_form "produits.resources.ProduitResource" %}
        {% djresource_form "produits.resources.ProduitResource" produit.pk %}
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    form_context = resource.get_form_context(request, lookup=lookup)
    template_name = resource._theme_template("form_partial", None)
    return mark_safe(render_to_string(template_name, form_context, request=request))


@register.simple_tag(takes_context=True)
def djresource_detail(context, resource_path, lookup):
    """
    Injects the fully rendered "detail" component of a specific object
    into the current template. `lookup` = value of the Resource's
    `lookup_field`.

    Usage:
        {% djresource_detail "produits.resources.ProduitResource" produit.pk %}
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    detail_context = resource.get_detail_context(request, lookup)
    template_name = resource._theme_template("detail_partial", None)
    return mark_safe(render_to_string(template_name, detail_context, request=request))


# ---------------------------------------------------------------------
# "Raw data" tags (no HTML — fully free-form display)
# ---------------------------------------------------------------------
@register.simple_tag(takes_context=True)
def djresource_list_data(context, resource_path):
    """
    Computes the list data WITHOUT rendering any HTML. Use with `as` to
    build your own display (cards, grid...).

    Usage:
        {% djresource_list_data "produits.resources.ProduitResource" as produits %}
        {% for produit in produits.object_list %}
          <a href="{% url produits.url_detail produit.pk %}">{{ produit.nom }}</a>
        {% endfor %}

    Note: use `produit.pk` (or the attribute corresponding to
    `lookup_field` if you customized it) in URLs, not an arbitrary
    identifier.
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    return resource.get_list_context(request)


@register.simple_tag(takes_context=True)
def djresource_form_data(context, resource_path, lookup=None):
    """
    Like `djresource_list_data`, for a form (create if `lookup` is
    omitted, update otherwise).

    Usage:
        {% djresource_form_data "produits.resources.ProduitResource" as f %}
        <form method="post" action="{{ f.form_action_url }}" enctype="multipart/form-data">
          {% csrf_token %}
          {% for field in f.form %}...{% endfor %}
        </form>
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    return resource.get_form_context(request, lookup=lookup)


@register.simple_tag(takes_context=True)
def djresource_detail_data(context, resource_path, lookup):
    """
    Like `djresource_list_data`, for the detail of a specific object.

    Usage:
        {% djresource_detail_data "produits.resources.ProduitResource" produit_id as d %}
        <h1>{{ d.object.nom }}</h1>
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    return resource.get_detail_context(request, lookup)
