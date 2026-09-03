"""
djresource.mixins
==================

Mixins utilisés pour composer dynamiquement les vues générées par `Resource`.

Chaque mixin ne fait qu'une seule chose et respecte la chaîne `super()`,
afin de pouvoir être librement combiné dans `Resource.get_*_view()` sans
écraser le comportement des autres mixins (voir resource.py).
"""
import uuid

from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404


# ---------------------------------------------------------------------
# Contexte commun (toutes les vues générées)
# ---------------------------------------------------------------------
class ResourceContextMixin:
    """
    Injecte la resource, les noms de routes utiles, et le contexte métier
    additionnel (via `Resource.get_extra_context()`) dans le contexte du
    template.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource = self.resource
        context["resource"] = resource
        context["verbose_name"] = resource.verbose_name
        context["verbose_name_plural"] = resource.model._meta.verbose_name_plural
        context["url_list"] = resource.url_name("list")
        context["url_create"] = resource.url_name("create")
        context["url_detail"] = resource.url_name("detail")
        context["url_update"] = resource.url_name("update")
        context["url_delete"] = resource.url_name("delete")

        extra = resource.get_extra_context(self)
        if extra:
            context.update(extra)
        return context


class ResourceListContextMixin(ResourceContextMixin):
    """Ajoute les colonnes à afficher (list_display) au contexte de la liste."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["list_display"] = self.resource.list_display
        return context


# ---------------------------------------------------------------------
# Recherche et tri (ListView uniquement)
# ---------------------------------------------------------------------
class ResourceSearchMixin:
    """
    Ajoute une recherche texte simple sur les champs déclarés dans
    `search_fields`, via le paramètre GET `?q=...`.
    """

    search_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query and self.search_fields:
            filters = Q()
            for field in self.search_fields:
                filters |= Q(**{f"{field}__icontains": query})
            qs = qs.filter(filters)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["search_enabled"] = bool(self.search_fields)
        return context


class ResourceOrderingMixin:
    """
    Permet de trier la liste via `?sort=champ&dir=asc|desc`, restreint
    aux champs déclarés dans `ordering_fields` (sécurité : on n'autorise
    pas de tri sur un champ arbitraire non prévu).
    """

    ordering_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        sort = self.request.GET.get("sort")
        direction = self.request.GET.get("dir", "asc")
        if sort and sort in self.ordering_fields:
            qs = qs.order_by(sort if direction == "asc" else f"-{sort}")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_sort"] = self.request.GET.get("sort", "")
        context["current_dir"] = self.request.GET.get("dir", "asc")
        return context


# ---------------------------------------------------------------------
# Résolution de l'objet via lookup_field (Detail / Update / Delete)
# ---------------------------------------------------------------------
class ResourceLookupMixin:
    """
    Résout l'objet via `resource.lookup_field` (par défaut "pk") au lieu de
    se reposer sur le pk Django. Permet des URLs propres : slug, uid, code...

    `lookup_field` peut être n'importe quel champ du modèle ("pk", "slug",
    "uid", "uuid", "code", ...). La valeur vient de l'URL (`self.kwargs`)
    sous forme de chaîne : on la convertit vers le bon type selon le champ
    (UUID, entier, chaîne) avant de filtrer le queryset.
    """

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        field_name = self.resource.lookup_field
        lookup_value = self.kwargs.get(field_name)

        # Aucune valeur de lookup dans l'URL : on laisse SingleObjectMixin
        # tenter sa résolution native (pk / slug), pour rester compatible.
        if lookup_value is None:
            return super().get_object(queryset=queryset)

        # Conversion de la chaîne d'URL vers le type du champ du modèle.
        if field_name == "pk":
            model_field = self.resource.model._meta.pk
        else:
            model_field = self.resource.model._meta.get_field(field_name)
        if isinstance(model_field, models.UUIDField):
            lookup_value = uuid.UUID(str(lookup_value))
        elif isinstance(model_field, (models.IntegerField, models.AutoField)):
            lookup_value = int(lookup_value)

        return get_object_or_404(queryset, **{field_name: lookup_value})


# ---------------------------------------------------------------------
# Messages de succès (Create / Update / Delete)
# ---------------------------------------------------------------------
class ResourceCreateMessageMixin:
    """Ajoute un message de succès (django.contrib.messages) après création."""

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            self.resource.success_message_create % {"name": self.resource.verbose_name},
        )
        return response


class ResourceUpdateMessageMixin:
    """Ajoute un message de succès après modification."""

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            self.resource.success_message_update % {"name": self.resource.verbose_name},
        )
        return response


class ResourceDeleteMessageMixin:
    """Ajoute un message de succès après suppression."""

    def form_valid(self, form):
        object_repr = str(self.object)
        response = super().form_valid(form)
        messages.success(
            self.request,
            self.resource.success_message_delete % {"name": object_repr},
        )
        return response
