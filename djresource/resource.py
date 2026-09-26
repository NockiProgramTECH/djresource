"""
djresource.resource
====================

Core of the library: the `Resource` class.

A `Resource` represents a Django model for which you want to automatically
generate the CRUD views (Create, Read, Update, Delete), the form and the
associated routes, without writing repetitive boilerplate.

Minimal example
----------------

    # produits/resources.py
    from djresource.resource import Resource
    from .models import Produit

    class ProduitResource(Resource):
        model = Produit
        fields = ["nom", "prix", "stock"]     # always list fields explicitly (see Security)
        list_display = ["nom", "prix", "stock"]
        search_fields = ["nom"]
        ordering_fields = ["nom", "prix"]

    # urls.py
    from django.urls import path, include
    from produits.resources import ProduitResource

    urlpatterns = [
        path("produits/", include(ProduitResource().urls())),
    ]

This automatically generates:
    /produits/                     -> list (search, sort, pagination)
    /produits/nouveau/             -> create
    /produits/<pk>/                -> detail
    /produits/<pk>/modifier/       -> update
    /produits/<pk>/supprimer/      -> delete (confirmation)

Identifying objects by something other than "pk" (lookup_field)
------------------------------------------------------------------
By default, the detail/update/delete URLs use the primary key (`pk`). To
use another field (e.g. a slug, or a name):

    class ProduitResource(Resource):
        model = Produit
        lookup_field = "slug"   # must be unique in the database (unique=True)

This generates `/produits/<slug>/`, etc. `lookup_field` MUST correspond to
a unique field on the model (`unique=True` or primary key), otherwise
several objects could match the same URL — a `UserWarning` is raised if
that's not the case.

Relations (ForeignKey, OneToOneField, ManyToManyField)
------------------------------------------------------------
Django natively handles relations in generated forms: a
ForeignKey/OneToOneField becomes a dropdown list (choices among related
objects, displayed via their `__str__`), a ManyToManyField becomes a
multi-select list. Nothing to configure for this to work.
For display (list/detail), the library also automatically resolves M2M
relations and reverse FKs (displayed as a readable comma-separated list).
Remember `select_related`/`prefetch_related` to avoid N+1 queries on
relations shown in `list_display`. See the README for full examples.

Three ways to display data (from simplest to most flexible)
----------------------------------------------------------------------
1. Library templates as-is (theme = "bootstrap"/"tailwind"/"plain").
2. Components injected into your own pages (`{% djresource_list %}` etc.).
3. Raw data (`{% djresource_list_data %}`, `get_list_context()`,
   etc.): no HTML imposed, fully free-form display. See README.md.
"""
from __future__ import annotations

import warnings

from django.forms import modelform_factory
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.core.paginator import Paginator
from django.db.models import Q

from .mixins import (
    ResourceContextMixin,
    ResourceCreateMessageMixin,
    ResourceDeleteMessageMixin,
    ResourceDeleteHooksMixin,
    ResourceSaveHooksMixin,
    ResourceInlineFormsetMixin,
    ResourceFilterMixin,
    ResourceFormActionMixin,
    ResourceListContextMixin,
    ResourceBulkActionsMixin,
    ResourceLookupMixin,
    ResourceOrderingMixin,
    ResourceQuerysetMixin,
    ResourceSearchMixin,
    ResourceUpdateMessageMixin,
)

# CSS classes automatically injected on form widgets, depending on the
# chosen theme (only used for fields not covered by `widget_classes`, and
# only if `auto_form_css = True`).
THEME_WIDGET_CLASSES = {
    "bootstrap": {
        "checkbox": "form-check-input",
        "select": "form-select",
        "default": "form-control",
    },
    "tailwind": {
        "checkbox": "h-4 w-4 text-blue-600 border-gray-300 rounded",
        "select": "border border-gray-300 rounded px-3 py-2 w-full",
        "default": "border border-gray-300 rounded px-3 py-2 w-full",
    },
    "plain": {
        "checkbox": "djr-checkbox",
        "select": "djr-input",
        "default": "djr-input",
    },
}

_BUILTIN_THEMES = {"bootstrap", "tailwind", "plain"}


class FieldsAllWarning(UserWarning):
    """
    Raised at instantiation when the legacy `fields = "__all__"` compatibility
    value is used. Explicitly list the fields allowed for writing.
    """


class Resource:
    """
    Base class to subclass in order to declare a CRUD resource.

    See the module docstring for the full list of options and, most
    importantly, the SECURITY section of the README before any production
    deployment.
    """

    model = None
    fields = []
    public = False
    inlines: list = []
    htmx = False
    bulk_actions: list = []
    readonly_fields: list = []
    list_display: list | None = None
    search_fields: list = []
    ordering_fields: list = []
    list_filter: list = []
    paginate_by = 20
    select_related: list = []
    prefetch_related: list = []

    # Field used to identify an object in URLs. "pk" by default.
    # lookup_url_kwarg/lookup_converter are inferred automatically if not
    # provided (see __init__).
    lookup_field = "pk"
    lookup_url_kwarg: str | None = None
    lookup_converter: str | None = None

    theme = "bootstrap"
    auto_form_css = True
    widget_classes: dict = {}   # {"field_name": "my-css-classes"} — takes priority over auto_form_css/theme
    widget_attrs: dict = {}     # {"field_name": {"data-x": "1", "maxlength": "50"}} — extra HTML attributes

    template_list = None
    template_form = None
    template_detail = None
    template_delete = None

    # Messages shown via django.contrib.messages. "%(name)s" is replaced by
    # the model's verbose_name (create/update) or by str(object) (delete).
    success_message_create = "%(name)s créé avec succès."
    success_message_update = "%(name)s modifié avec succès."
    success_message_delete = "%(name)s supprimé avec succès."

    def clean(self, instance, request):
        """Validate before saving; raise ValidationError to reject the form."""
        pass

    def before_save(self, instance, request, is_new):
        """Modify the instance immediately before saving (no database write yet)."""
        pass

    def after_save(self, instance, request, is_new):
        """React after parent and M2M saving, before inlines; pk is available.

        For external side effects use transaction.on_commit when appropriate.
        """
        pass

    def before_delete(self, instance, request):
        """Raise ValidationError to prevent deletion."""
        pass

    def after_delete(self, instance, request):
        """React after deletion; Django has cleared instance.pk."""
        pass

    def __init__(self):
        if self.model is None:
            raise ValueError(
                f"{self.__class__.__name__} must define the 'model' attribute."
            )
        self.name = self.model._meta.model_name  # e.g. "produit"
        self.verbose_name = str(self.model._meta.verbose_name)
        self.app_label = self.model._meta.app_label

        if self.list_display is None:
            self.list_display = [f.name for f in self.model._meta.fields]

        # Resolve lookup_url_kwarg / lookup_converter if not provided
        self.lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if self.lookup_converter is None:
            self.lookup_converter = self._default_lookup_converter()

        self._warn_if_lookup_field_not_unique()

        if self.fields == "__all__":
            warnings.warn(
                f"{self.__class__.__name__}: fields='__all__' exposes all "
                f"fields of the {self.model.__name__} model in the form. "
                "Explicitly list the fields allowed for writing.",
                FieldsAllWarning,
                stacklevel=2,
            )

    def _default_lookup_converter(self) -> str:
        """
        Infers the Django URL converter from the `lookup_field`'s type
        (`int` for pk, `slug` for a SlugField, `uuid` for a UUIDField,
        `str` otherwise). Overridable via `lookup_converter`.
        """
        if self.lookup_field == "pk":
            return "int"
        try:
            from django.db import models as dj_models

            field_obj = self.model._meta.get_field(self.lookup_field)
        except Exception:
            return "str"
        if isinstance(field_obj, dj_models.SlugField):
            return "slug"
        if isinstance(field_obj, dj_models.UUIDField):
            return "uuid"
        if isinstance(field_obj, dj_models.IntegerField):
            return "int"
        return "str"

    def get_lookup_url(self) -> str:
        """
        URL segment used to identify an object, e.g. `<int:pk>`,
        `<slug:slug>`, `<uuid:uid>`. Used by `.urls()`.
        """
        return f"<{self.lookup_converter}:{self.lookup_url_kwarg}>"

    def _warn_if_lookup_field_not_unique(self):
        """
        `lookup_field` must be unique in the database to identify a single
        object per URL. We warn (without blocking) if this is visibly not
        the case — a frequent cause of a "MultipleObjectsReturned" bug
        that's hard to diagnose later.
        """
        if self.lookup_field == "pk":
            return
        try:
            field_obj = self.model._meta.get_field(self.lookup_field)
        except Exception:
            return
        is_unique = getattr(field_obj, "unique", False) or getattr(field_obj, "primary_key", False)
        if not is_unique:
            warnings.warn(
                f"{self.__class__.__name__}: lookup_field='{self.lookup_field}' is not "
                f"unique=True on the {self.model.__name__} model. If two records "
                "share the same value, the generated URLs will fail (server error). "
                "Add unique=True to the field, or use another field (e.g. a SlugField).",
                stacklevel=3,
            )

    # ------------------------------------------------------------------
    # Additional business context (main extension hook)
    # ------------------------------------------------------------------
    def get_extra_context(self, view):
        """
        Override to inject additional business data into the context of
        ANY generated view — without having to rewrite the views. `view`
        can be None outside of a Django view.
        """
        return {}

    # ------------------------------------------------------------------
    # Template resolution based on theme
    # ------------------------------------------------------------------
    def _theme_template(self, kind: str, explicit: str | None) -> str:
        """
        Resolves the template path to use for `kind`.
        Priority: explicit template > "bootstrap" theme (historical,
        `djresource/<kind>.html`) > other theme (`djresource/<theme>/<kind>.html`).
        """
        if explicit:
            return explicit
        if self.theme == "bootstrap":
            return f"djresource/{kind}.html"
        return f"djresource/{self.theme}/{kind}.html"

    # ------------------------------------------------------------------
    # Identifying an object (lookup_field)
    # ------------------------------------------------------------------
    def get_lookup_value(self, obj):
        """Returns the value of the field used to identify `obj` in URLs."""
        return getattr(obj, self.lookup_field)

    # ------------------------------------------------------------------
    # Form
    # ------------------------------------------------------------------
    def get_form_class(self):
        """
        Builds a ModelForm from the model. Relations (ForeignKey,
        OneToOneField, ManyToManyField) are handled natively by Django:
        dropdown list for simple relations, multi-select for ManyToMany —
        no extra configuration is needed for them to appear in the form as
        long as they're listed in `fields`.

        Also applies:
        - per-field CSS classes: `widget_classes[field]` if provided,
          otherwise theme classes if `auto_form_css = True`,
        - extra HTML attributes per field (`widget_attrs[field]`),
        - disabled `readonly_fields` (Django ignores the submitted value
          for a field with `disabled=True`, which can't be bypassed by
          tampering with the POST data).
        """
        form_class = modelform_factory(self.model, fields=self.fields)
        readonly_fields = self.readonly_fields
        auto_form_css = self.auto_form_css
        widget_classes = self.widget_classes
        widget_attrs = self.widget_attrs
        css_classes = THEME_WIDGET_CLASSES.get(self.theme, THEME_WIDGET_CLASSES["plain"])
        original_init = form_class.__init__

        def patched_init(self_form, *args, **kwargs):
            original_init(self_form, *args, **kwargs)
            for field_name, field in self_form.fields.items():
                if field_name in widget_classes:
                    field.widget.attrs["class"] = widget_classes[field_name]
                elif auto_form_css:
                    widget_name = field.widget.__class__.__name__
                    if widget_name == "CheckboxInput":
                        css_class = css_classes["checkbox"]
                    elif widget_name in ("Select", "SelectMultiple"):
                        css_class = css_classes["select"]
                    else:
                        css_class = css_classes["default"]
                    existing = field.widget.attrs.get("class", "")
                    field.widget.attrs["class"] = f"{existing} {css_class}".strip()

                if field_name in widget_attrs:
                    field.widget.attrs.update(widget_attrs[field_name])

                if field_name in readonly_fields:
                    field.disabled = True

        form_class.__init__ = patched_init
        return form_class

    # ------------------------------------------------------------------
    # Common queryset (List / Detail / Update / Delete)
    # ------------------------------------------------------------------
    def get_base_queryset(self):
        """
        Base queryset before request-specific authorization scoping.
        """
        qs = self.model._default_manager.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)
        return qs

    def scope_queryset(self, queryset, request=None):
        """
        Restrict objects visible to the current request.

        Override this method for tenant/owner isolation. It is applied to
        list, detail, update, and delete views, as well as injected contexts.
        """
        return queryset

    def get_queryset(self, request=None):
        """Return the fully request-scoped queryset for all CRUD operations."""
        return self.scope_queryset(self.get_base_queryset(), request)

    # ------------------------------------------------------------------
    # List filtering (list_filter)
    # ------------------------------------------------------------------
    def get_active_list_filters(self, params):
        """
        Validates filter parameters (`?field=value`, restricted to
        `list_filter` fields). Returns {field: value} — empty or invalid
        values are ignored (no filter).
        """
        from django.db import models as dj_models

        active = {}
        if not params:
            return active
        for field_name in self.list_filter:
            raw = params.get(field_name, "")
            if raw in ("", None):
                continue
            try:
                field_obj = self.model._meta.get_field(field_name)
            except Exception:
                continue
            try:
                active[field_name] = self._parse_filter_value(field_obj, raw)
            except ValueError:
                continue
        return active

    @staticmethod
    def _parse_filter_value(field_obj, raw):
        """Converts a raw GET value into a filter value (or raises ValueError)."""
        from django.db import models as dj_models

        if isinstance(field_obj, dj_models.BooleanField):
            normalized = str(raw).strip().lower()
            if normalized in ("1", "true", "oui", "yes"):
                return True
            if normalized in ("0", "false", "non", "no"):
                return False
            raise ValueError(f"Invalid boolean value: {raw!r}")
        if field_obj.choices:
            valid = {str(key) for key, _label in field_obj.choices}
            if str(raw) in valid:
                return raw
            raise ValueError(f"Value not in choices: {raw!r}")
        return raw

    def apply_list_filters(self, qs, params):
        """Applies the active filters (`list_filter`) to the queryset (combined with AND)."""
        for field_name, value in self.get_active_list_filters(params).items():
            qs = qs.filter(**{field_name: value})
        return qs

    def get_list_filter_options(self, params, request=None):
        """
        Options for the `<select>` elements in `_filters.html`:
        [{field, options: [{value, label, selected}]}]. "Tous" (empty
        value) disables the filter on that field.
        """
        from django.db import models as dj_models

        result = []
        for field_name in self.list_filter:
            try:
                field_obj = self.model._meta.get_field(field_name)
            except Exception:
                continue
            current = params.get(field_name, "") if params else ""
            current = "" if current is None else str(current)
            options = [{"value": "", "label": "Tous", "selected": current == ""}]
            if isinstance(field_obj, dj_models.BooleanField):
                options += [
                    {"value": "1", "label": "Oui", "selected": current == "1"},
                    {"value": "0", "label": "Non", "selected": current == "0"},
                ]
            elif field_obj.choices:
                for key, label in field_obj.choices:
                    options.append({
                        "value": str(key),
                        "label": str(label),
                        "selected": current == str(key),
                    })
            else:
                distinct = (
                    self.get_queryset(request)
                    .order_by(field_name)
                    .values_list(field_name, flat=True)
                    .distinct()
                )
                for val in distinct:
                    options.append({
                        "value": str(val),
                        "label": str(val),
                        "selected": current == str(val),
                    })
            result.append({"field": field_name, "options": options})
        return result

    # ------------------------------------------------------------------
    # Permissions (hook to override in a subclass)
    # ------------------------------------------------------------------
    def get_permissions(self):
        """
        Override to return a list of Django mixins/permission classes
        (e.g. [LoginRequiredMixin]), inserted into the MRO of the
        generated views. Resources are protected by LoginRequiredMixin by
        default; set ``public = True`` explicitly for a public resource.
        """
        if self.public:
            return []
        from django.contrib.auth.mixins import LoginRequiredMixin

        return [LoginRequiredMixin]

    def _enforce_permissions(self, request):
        """
        Runs the same permission mixin dispatch chain used by full views.
        This includes UserPassesTestMixin and custom business permission
        mixins, not only LoginRequiredMixin/PermissionRequiredMixin.
        """
        from django.views import View

        if request is None:
            raise ValueError("A request is required to enforce Resource permissions.")
        permissions = self.get_permissions()
        if not permissions:
            return

        permission_view = type(
            f"{self.name.title()}PermissionProbe",
            (*permissions, View),
            self._permission_view_attrs(),
        )()
        permission_view.setup(request)
        response = permission_view.dispatch(request)
        if getattr(response, "status_code", 200) in (301, 302, 303, 307, 308):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("Authentication required to access this resource.")

    def _permission_view_attrs(self):
        """Attributes shared by generated views and the partial permission probe."""
        attrs = {"resource": self}
        for attr_name in (
            "permission_required",
            "raise_exception",
            "login_url",
            "redirect_field_name",
        ):
            if hasattr(self, attr_name):
                attrs[attr_name] = getattr(self, attr_name)
        if hasattr(self, "test_func"):
            attrs["test_func"] = lambda view: self.test_func(view.request)
        return attrs

    def get_bulk_actions(self, request):
        """Return validated action dicts; override for request-specific actions.

        Accepts objects or dicts with unique nonempty name, label, callable run.
        Returning an action only registers it; has_bulk_action_permission is
        checked independently before execution. Never mutate shared class lists.
        """
        from django.core.exceptions import ImproperlyConfigured

        actions = []
        names = set()
        for action in self.bulk_actions:
            get = action.get if isinstance(action, dict) else lambda key: getattr(action, key, None)
            name, label, run = get("name"), get("label"), get("run")
            if not isinstance(name, str) or not name or name in names or not label or not callable(run):
                raise ImproperlyConfigured("Bulk actions need unique names, labels and callable run(queryset, request).")
            names.add(name)
            actions.append({"name": name, "label": label, "run": run})
        return actions

    def has_bulk_action_permission(self, action, request):
        """Additional action authorization, after normal list permissions.

        Defaults to True: registering an action enables it for every user allowed
        to access the list (including anonymous users on public resources).
        Override for model/business permissions. Per-object checks, if needed,
        belong in run(); its queryset is already scoped and filtered.
        """
        return True

    def get_bulk_context(self, request):
        """Controls shared by generated lists and injected components.

        POST always targets the generated list, retaining the current query
        parameters. Actions receive primary keys, independently of lookup_field.
        """
        actions = [
            {"name": action["name"], "label": action["label"]}
            for action in self.get_bulk_actions(request)
            if self.has_bulk_action_permission(action, request)
        ]
        url = self.get_success_url_list() if actions else ""
        if actions and request is not None and request.GET:
            url += "?" + request.GET.urlencode()
        return {"bulk_actions": actions, "bulk_action_url": url}

    # ------------------------------------------------------------------
    # Route names
    # ------------------------------------------------------------------
    def url_name(self, action: str) -> str:
        return f"{self.name}_{action}"

    def get_success_url_list(self):
        return reverse(self.url_name("list"))

    # ------------------------------------------------------------------
    # Context computed outside a view (for injection into a custom page)
    # ------------------------------------------------------------------
    def _base_url_context(self):
        return {
            "resource": self,
            "verbose_name": self.verbose_name,
            "verbose_name_plural": self.model._meta.verbose_name_plural,
            "url_list": self.url_name("list"),
            "url_create": self.url_name("create"),
            "url_detail": self.url_name("detail"),
            "url_update": self.url_name("update"),
            "url_delete": self.url_name("delete"),
        }

    def get_list_context(self, request):
        """
        Computes the full context of a list (search, filters, sorting,
        pagination) without going through a ListView. See README "Level 3".
        """
        self._enforce_permissions(request)
        qs = self.get_queryset(request)

        query = request.GET.get("q", "").strip() if request else ""
        if query and self.search_fields:
            filters = Q()
            for field in self.search_fields:
                filters |= Q(**{f"{field}__icontains": query})
            qs = qs.filter(filters)

        params = request.GET if request else {}
        qs = self.apply_list_filters(qs, params)

        sort = request.GET.get("sort") if request else None
        direction = request.GET.get("dir", "asc") if request else "asc"
        if sort and sort in self.ordering_fields:
            qs = qs.order_by(sort if direction == "asc" else f"-{sort}")

        paginator = Paginator(qs, self.paginate_by)
        page_number = request.GET.get("page") if request else None
        page_obj = paginator.get_page(page_number)

        context = self._base_url_context()
        context.update(self.get_bulk_context(request))
        context.update({
            "object_list": page_obj.object_list,
            "list_display": self.list_display,
            "search_enabled": bool(self.search_fields),
            "search_query": query,
            "filters_enabled": bool(self.list_filter),
            "list_filters": self.get_list_filter_options(params, request),
            "current_sort": sort or "",
            "current_dir": direction,
            "is_paginated": paginator.num_pages > 1,
            "page_obj": page_obj,
            "paginator": paginator,
        })
        return context

    def get_form_context(self, request, lookup=None):
        """
        Computes the context of a create form (`lookup=None`) or an
        update form (`lookup` = value of `lookup_field`, `pk` by
        default). Does not itself handle the POST submission: the
        template explicitly points (`form_action_url`) to the URL
        generated by the library, which handles validation, saving and
        redirection.

        `get_object_or_404`: a non-existent lookup value returns a clean
        404 instead of an unhandled exception.
        """
        self._enforce_permissions(request)
        form_class = self.get_form_class()
        instance = None
        if lookup is not None:
            instance = get_object_or_404(
                self.get_queryset(request), **{self.lookup_field: lookup}
            )
        form = form_class(instance=instance)

        context = self._base_url_context()
        context.update({
            "form": form,
            "inline_formsets": [
                inline.get_formset_class(self.model)(instance=instance)
                for inline in self.inlines
            ],
            "object": instance,
            "form_action_url": (
                reverse(self.url_name("update"), args=[self.get_lookup_value(instance)])
                if instance is not None
                else reverse(self.url_name("create"))
            ),
        })
        return context

    def get_detail_context(self, request, lookup):
        """
        Computes the detail context of a specific object (`lookup` =
        value of `lookup_field`, `pk` by default). Non-existent lookup ->
        clean 404.
        """
        self._enforce_permissions(request)
        instance = get_object_or_404(
            self.get_queryset(request), **{self.lookup_field: lookup}
        )
        context = self._base_url_context()
        context["object"] = instance
        return context

    # ------------------------------------------------------------------
    # View generation (dynamic CBVs via type())
    # ------------------------------------------------------------------
    def get_list_view(self):
        resource = self
        bases = (
            ResourceListContextMixin,
            ResourceBulkActionsMixin,
            ResourceSearchMixin,
            ResourceOrderingMixin,
            ResourceFilterMixin,
            *self.get_permissions(),
            ResourceQuerysetMixin,
            ListView,
        )
        attrs = {
            **self._permission_view_attrs(),
            "model": self.model,
            "partial_template_kind": "list_partial",
            "template_name": self._theme_template("list", self.template_list),
            "paginate_by": self.paginate_by,
            "context_object_name": "object_list",
            "search_fields": self.search_fields,
            "ordering_fields": self.ordering_fields,
        }
        return type(f"{self.name.title()}ListView", bases, attrs)

    def get_detail_view(self):
        resource = self
        bases = (
            ResourceContextMixin,
            ResourceLookupMixin,
            *self.get_permissions(),
            ResourceQuerysetMixin,
            DetailView,
        )
        attrs = {
            **self._permission_view_attrs(),
            "model": self.model,
            "partial_template_kind": "detail_partial",
            "template_name": self._theme_template("detail", self.template_detail),
            "context_object_name": "object",
        }
        return type(f"{self.name.title()}DetailView", bases, attrs)

    def get_create_view(self):
        resource = self
        bases = (
            ResourceContextMixin,
            ResourceFormActionMixin,
            ResourceCreateMessageMixin,
            ResourceInlineFormsetMixin,
            ResourceSaveHooksMixin,
            *self.get_permissions(),
            ResourceQuerysetMixin,
            CreateView,
        )
        attrs = {
            **self._permission_view_attrs(),
            "model": self.model,
            "form_class": self.get_form_class(),
            "partial_template_kind": "form_partial",
            "template_name": self._theme_template("form", self.template_form),
            "get_success_url": lambda self_view: resource.get_success_url_list(),
        }
        return type(f"{self.name.title()}CreateView", bases, attrs)

    def get_update_view(self):
        resource = self
        bases = (
            ResourceContextMixin,
            ResourceFormActionMixin,
            ResourceLookupMixin,
            ResourceUpdateMessageMixin,
            ResourceInlineFormsetMixin,
            ResourceSaveHooksMixin,
            *self.get_permissions(),
            ResourceQuerysetMixin,
            UpdateView,
        )
        attrs = {
            **self._permission_view_attrs(),
            "model": self.model,
            "form_class": self.get_form_class(),
            "partial_template_kind": "form_partial",
            "template_name": self._theme_template("form", self.template_form),
            "get_success_url": lambda self_view: resource.get_success_url_list(),
        }
        return type(f"{self.name.title()}UpdateView", bases, attrs)

    def get_delete_view(self):
        resource = self
        bases = (
            ResourceContextMixin,
            ResourceLookupMixin,
            ResourceDeleteHooksMixin,
            ResourceDeleteMessageMixin,
            *self.get_permissions(),
            ResourceQuerysetMixin,
            DeleteView,
        )
        attrs = {
            **self._permission_view_attrs(),
            "model": self.model,
            "partial_template_kind": "confirm_delete_partial",
            "template_name": self._theme_template("confirm_delete", self.template_delete),
            "get_success_url": lambda self_view: resource.get_success_url_list(),
        }
        return type(f"{self.name.title()}DeleteView", bases, attrs)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    def urls(self):
        """
        Returns the list of CRUD routes ready to be wired into urls.py
        via `include(MyResource().urls())`. The object-identification URL
        segment uses `get_lookup_url()` (default: `<int:pk>`).
        """
        lookup_segment = self.get_lookup_url()
        return [
            path("", self.get_list_view().as_view(), name=self.url_name("list")),
            path("nouveau/", self.get_create_view().as_view(), name=self.url_name("create")),
            path(f"{lookup_segment}/", self.get_detail_view().as_view(), name=self.url_name("detail")),
            path(f"{lookup_segment}/modifier/", self.get_update_view().as_view(), name=self.url_name("update")),
            path(f"{lookup_segment}/supprimer/", self.get_delete_view().as_view(), name=self.url_name("delete")),
        ]
