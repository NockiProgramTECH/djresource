"""
djresource.resource
====================

Cœur du framework : la classe `Resource`.

Une `Resource` représente un modèle Django pour lequel on souhaite générer
automatiquement les vues CRUD (Create, Read, Update, Delete), le formulaire
et les routes associées, sans avoir à écrire de code répétitif.

Exemple minimal
----------------

    # produits/resources.py
    from djresource.resource import Resource
    from .models import Produit

    class ProduitResource(Resource):
        model = Produit
        fields = ["nom", "prix", "stock"]     # toujours lister explicitement les champs (voir Sécurité)
        list_display = ["nom", "prix", "stock"]
        search_fields = ["nom"]
        ordering_fields = ["nom", "prix"]

    # urls.py
    from django.urls import path, include
    from produits.resources import ProduitResource

    urlpatterns = [
        path("produits/", include(ProduitResource().urls())),
    ]

Cela génère automatiquement :
    /produits/                     -> liste (recherche, tri, pagination)
    /produits/nouveau/             -> création
    /produits/<pk>/                -> détail
    /produits/<pk>/modifier/       -> modification
    /produits/<pk>/supprimer/      -> suppression (confirmation)

Identifier les objets par autre chose que "pk" (lookup_field)
------------------------------------------------------------------
Par défaut, les URLs de détail/modification/suppression utilisent la clé
primaire (`pk`). Pour utiliser un autre champ (ex: un slug, ou un nom) :

    class ProduitResource(Resource):
        model = Produit
        lookup_field = "slug"   # doit être unique en base (unique=True)

Cela génère `/produits/<slug>/`, etc. `lookup_field` DOIT correspondre à
un champ unique sur le modèle (`unique=True` ou clé primaire), sinon
plusieurs objets pourraient correspondre à la même URL — une alerte
`UserWarning` est émise si ce n'est pas le cas.

Relations (ForeignKey, OneToOneField, ManyToManyField)
------------------------------------------------------------
Django gère nativement les relations dans les formulaires générés : une
ForeignKey/OneToOneField devient une liste déroulante (choix parmi les
objets liés, affichés via leur `__str__`), une ManyToManyField devient une
liste à sélection multiple. Rien à configurer pour que ça fonctionne.
Pour l'affichage (liste/détail), le framework résout aussi automatiquement
les relations M2M et les FK inversées (affichage sous forme de liste
lisible séparée par des virgules). Pensez à `select_related`/
`prefetch_related` pour éviter les requêtes N+1 sur les relations
affichées dans `list_display`. Voir README pour des exemples complets.

Trois façons d'afficher les données (du plus simple au plus libre)
----------------------------------------------------------------------
1. Templates du framework tels quels (theme = "bootstrap"/"tailwind"/"plain").
2. Composants injectés dans vos pages (`{% djresource_list %}` etc.).
3. Données brutes (`{% djresource_list_data %}`, `get_list_context()`,
   etc.) : aucun HTML imposé, affichage 100% libre. Voir README.md.
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
    ResourceFormActionMixin,
    ResourceListContextMixin,
    ResourceLookupMixin,
    ResourceOrderingMixin,
    ResourceSearchMixin,
    ResourceUpdateMessageMixin,
)

# Classes CSS injectées automatiquement sur les widgets du formulaire, selon
# le thème choisi (utilisées seulement pour les champs non couverts par
# `widget_classes`, et seulement si `auto_form_css = True`).
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


class Resource:
    """
    Classe de base à hériter pour déclarer une ressource CRUD.

    Voir le docstring du module pour la liste complète des options et,
    surtout, la section SÉCURITÉ du README avant tout déploiement en
    production.
    """

    model = None
    fields = "__all__"
    readonly_fields: list = []
    list_display: list | None = None
    search_fields: list = []
    ordering_fields: list = []
    paginate_by = 20
    select_related: list = []
    prefetch_related: list = []

    # Champ utilisé pour identifier un objet dans les URLs. "pk" par
    # défaut. lookup_url_kwarg/lookup_converter sont déduits automatiquement
    # si non fournis (voir __init__).
    lookup_field = "pk"
    lookup_url_kwarg: str | None = None
    lookup_converter: str | None = None

    theme = "bootstrap"
    auto_form_css = True
    widget_classes: dict = {}   # {"nom_champ": "mes-classes-css"} — prioritaire sur auto_form_css/theme
    widget_attrs: dict = {}     # {"nom_champ": {"data-x": "1", "maxlength": "50"}} — attributs HTML additionnels

    template_list = None
    template_form = None
    template_detail = None
    template_delete = None

    # Messages affichés via django.contrib.messages. "%(name)s" est remplacé
    # par le verbose_name du modèle (create/update) ou par str(objet) (delete).
    success_message_create = "%(name)s créé avec succès."
    success_message_update = "%(name)s modifié avec succès."
    success_message_delete = "%(name)s supprimé avec succès."

    def __init__(self):
        if self.model is None:
            raise ValueError(
                f"{self.__class__.__name__} doit définir l'attribut 'model'."
            )
        self.name = self.model._meta.model_name  # ex : "produit"
        self.verbose_name = str(self.model._meta.verbose_name)
        self.app_label = self.model._meta.app_label

        if self.list_display is None:
            self.list_display = [f.name for f in self.model._meta.fields]

        # Résolution de lookup_url_kwarg / lookup_converter si non fournis
        self.lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if self.lookup_converter is None:
            self.lookup_converter = "int" if self.lookup_field == "pk" else "str"

        self._warn_if_lookup_field_not_unique()

    def _warn_if_lookup_field_not_unique(self):
        """
        `lookup_field` doit être unique en base pour identifier un seul
        objet par URL. On avertit (sans bloquer) si ce n'est visiblement
        pas le cas — cause fréquente d'un bug "MultipleObjectsReturned"
        difficile à diagnostiquer plus tard.
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
                f"{self.__class__.__name__} : lookup_field='{self.lookup_field}' n'est pas "
                f"unique=True sur le modèle {self.model.__name__}. Si deux enregistrements "
                "partagent la même valeur, les URLs générées échoueront (erreur serveur). "
                "Ajoutez unique=True au champ, ou utilisez un autre champ (ex: un SlugField).",
                stacklevel=3,
            )

    # ------------------------------------------------------------------
    # Contexte métier additionnel (hook d'extension principal)
    # ------------------------------------------------------------------
    def get_extra_context(self, view):
        """
        À surcharger pour injecter des données métier supplémentaires dans
        le contexte de N'IMPORTE QUELLE vue générée — sans avoir à
        réécrire les vues. `view` peut être None hors d'une vue Django.
        """
        return {}

    # ------------------------------------------------------------------
    # Résolution des templates selon le thème
    # ------------------------------------------------------------------
    def _theme_template(self, kind: str, explicit: str | None) -> str:
        """
        Résout le chemin du template à utiliser pour `kind`.
        Priorité : template explicite > thème "bootstrap" (historique,
        `djresource/<kind>.html`) > autre thème (`djresource/<theme>/<kind>.html`).
        """
        if explicit:
            return explicit
        if self.theme == "bootstrap":
            return f"djresource/{kind}.html"
        return f"djresource/{self.theme}/{kind}.html"

    # ------------------------------------------------------------------
    # Identification d'un objet (lookup_field)
    # ------------------------------------------------------------------
    def get_lookup_value(self, obj):
        """Retourne la valeur du champ utilisé pour identifier `obj` dans les URLs."""
        return getattr(obj, self.lookup_field)

    # ------------------------------------------------------------------
    # Formulaire
    # ------------------------------------------------------------------
    def get_form_class(self):
        """
        Construit un ModelForm à partir du modèle. Les relations
        (ForeignKey, OneToOneField, ManyToManyField) sont gérées
        nativement par Django : liste déroulante pour les relations
        simples, sélection multiple pour ManyToMany — aucune configuration
        supplémentaire n'est nécessaire pour qu'elles apparaissent dans le
        formulaire si elles sont listées dans `fields`.

        Applique aussi :
        - classes CSS par champ : `widget_classes[field]` si fourni,
          sinon classes du thème si `auto_form_css = True`,
        - attributs HTML additionnels par champ (`widget_attrs[field]`),
        - champs `readonly_fields` désactivés (Django ignore la valeur
          soumise pour un champ `disabled=True`, impossible à contourner
          en modifiant le POST).
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
    # Queryset commun (List / Detail / Update / Delete)
    # ------------------------------------------------------------------
    def get_base_queryset(self):
        """
        Queryset de base utilisé par toutes les vues. À surcharger pour
        restreindre l'accès (ex : filtrer par propriétaire) — voir
        avertissement sécurité dans le README : ce filtrage n'est PAS
        fait automatiquement en V1.
        """
        qs = self.model._default_manager.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)
        return qs

    # ------------------------------------------------------------------
    # Permissions (hook à surcharger dans une sous-classe)
    # ------------------------------------------------------------------
    def get_permissions(self):
        """
        À surcharger pour retourner une liste de mixins/permission classes
        Django (ex: [LoginRequiredMixin]), insérés dans le MRO des vues
        générées. ATTENTION : retourne [] par défaut (aucune restriction).
        """
        return []

    # ------------------------------------------------------------------
    # Noms de routes
    # ------------------------------------------------------------------
    def url_name(self, action: str) -> str:
        return f"{self.name}_{action}"

    def get_success_url_list(self):
        return reverse(self.url_name("list"))

    # ------------------------------------------------------------------
    # Contexte calculé hors vue (pour injection dans une page personnalisée)
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
        Calcule le contexte complet d'une liste (recherche, tri,
        pagination) sans passer par une ListView. Voir README "Niveau 3".
        """
        qs = self.get_base_queryset()

        query = request.GET.get("q", "").strip() if request else ""
        if query and self.search_fields:
            filters = Q()
            for field in self.search_fields:
                filters |= Q(**{f"{field}__icontains": query})
            qs = qs.filter(filters)

        sort = request.GET.get("sort") if request else None
        direction = request.GET.get("dir", "asc") if request else "asc"
        if sort and sort in self.ordering_fields:
            qs = qs.order_by(sort if direction == "asc" else f"-{sort}")

        paginator = Paginator(qs, self.paginate_by)
        page_number = request.GET.get("page") if request else None
        page_obj = paginator.get_page(page_number)

        context = self._base_url_context()
        context.update({
            "object_list": page_obj.object_list,
            "list_display": self.list_display,
            "search_enabled": bool(self.search_fields),
            "search_query": query,
            "current_sort": sort or "",
            "current_dir": direction,
            "is_paginated": paginator.num_pages > 1,
            "page_obj": page_obj,
            "paginator": paginator,
        })
        return context

    def get_form_context(self, request, lookup=None):
        """
        Calcule le contexte d'un formulaire de création (`lookup=None`)
        ou de modification (`lookup` = valeur du `lookup_field`, `pk` par
        défaut). Ne gère pas la soumission POST elle-même : le template
        pointe explicitement (`form_action_url`) vers l'URL générée par
        le framework, qui gère validation, sauvegarde et redirection.

        `get_object_or_404` : une valeur de lookup inexistante renvoie une
        404 propre plutôt qu'une exception non gérée.
        """
        form_class = self.get_form_class()
        instance = None
        if lookup is not None:
            instance = get_object_or_404(self.get_base_queryset(), **{self.lookup_field: lookup})
        form = form_class(instance=instance)

        context = self._base_url_context()
        context.update({
            "form": form,
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
        Calcule le contexte du détail d'un objet précis (`lookup` = valeur
        du `lookup_field`, `pk` par défaut). Lookup inexistant -> 404 propre.
        """
        instance = get_object_or_404(self.get_base_queryset(), **{self.lookup_field: lookup})
        context = self._base_url_context()
        context["object"] = instance
        return context

    # ------------------------------------------------------------------
    # Génération des vues (CBV dynamiques via type())
    # ------------------------------------------------------------------
    def get_list_view(self):
        resource = self
        bases = (
            ResourceListContextMixin,
            ResourceSearchMixin,
            ResourceOrderingMixin,
            *self.get_permissions(),
            ListView,
        )
        attrs = {
            "resource": resource,
            "model": self.model,
            "queryset": self.get_base_queryset(),
            "template_name": self._theme_template("list", self.template_list),
            "paginate_by": self.paginate_by,
            "context_object_name": "object_list",
            "search_fields": self.search_fields,
            "ordering_fields": self.ordering_fields,
        }
        return type(f"{self.name.title()}ListView", bases, attrs)

    def get_detail_view(self):
        resource = self
        bases = (ResourceContextMixin, ResourceLookupMixin, *self.get_permissions(), DetailView)
        attrs = {
            "resource": resource,
            "model": self.model,
            "queryset": self.get_base_queryset(),
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
            *self.get_permissions(),
            CreateView,
        )
        attrs = {
            "resource": resource,
            "model": self.model,
            "form_class": self.get_form_class(),
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
            *self.get_permissions(),
            UpdateView,
        )
        attrs = {
            "resource": resource,
            "model": self.model,
            "queryset": self.get_base_queryset(),
            "form_class": self.get_form_class(),
            "template_name": self._theme_template("form", self.template_form),
            "get_success_url": lambda self_view: resource.get_success_url_list(),
        }
        return type(f"{self.name.title()}UpdateView", bases, attrs)

    def get_delete_view(self):
        resource = self
        bases = (
            ResourceContextMixin,
            ResourceLookupMixin,
            ResourceDeleteMessageMixin,
            *self.get_permissions(),
            DeleteView,
        )
        attrs = {
            "resource": resource,
            "model": self.model,
            "queryset": self.get_base_queryset(),
            "template_name": self._theme_template("confirm_delete", self.template_delete),
            "get_success_url": lambda self_view: resource.get_success_url_list(),
        }
        return type(f"{self.name.title()}DeleteView", bases, attrs)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    def urls(self):
        """
        Retourne la liste de routes CRUD prêtes à être branchées dans
        urls.py via `include(MaResource().urls())`. Le segment d'URL
        d'identification utilise `lookup_converter`/`lookup_url_kwarg`
        (par défaut : `<int:pk>`).
        """
        converter = self.lookup_converter
        kwarg = self.lookup_url_kwarg
        lookup_segment = f"<{converter}:{kwarg}>"
        return [
            path("", self.get_list_view().as_view(), name=self.url_name("list")),
            path("nouveau/", self.get_create_view().as_view(), name=self.url_name("create")),
            path(f"{lookup_segment}/", self.get_detail_view().as_view(), name=self.url_name("detail")),
            path(f"{lookup_segment}/modifier/", self.get_update_view().as_view(), name=self.url_name("update")),
            path(f"{lookup_segment}/supprimer/", self.get_delete_view().as_view(), name=self.url_name("delete")),
        ]
