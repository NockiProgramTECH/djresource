"""
djresource.resource
====================

Cœur de la bibliothèque : la classe `Resource`.

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

Personnalisation visuelle (thèmes)
-----------------------------------
La bibliothèque fournit 3 thèmes de templates prêts à l'emploi, choisis via
l'attribut `theme` :

    theme = "bootstrap"   (par défaut) -> Bootstrap 5 via CDN
    theme = "tailwind"                 -> Tailwind via CDN
    theme = "plain"                    -> HTML sémantique + CSS minimal
                                           (djresource/static/djresource/css/djresource.css),
                                           pensé pour être entièrement réécrit à la main.

On peut aussi surcharger un template précis (indépendamment du thème) via
`template_list`, `template_detail`, `template_form`, `template_delete`, ou
désactiver l'injection automatique de classes CSS sur le formulaire avec
`auto_form_css = False` si on préfère tout coder à la main.

Ajouter des informations non-CRUD (contexte métier + blocks de template)
--------------------------------------------------------------------------
En pratique un CRUD généré affiche rarement QUE les champs du modèle. Deux
mécanismes permettent d'enrichir les vues sans les réécrire :

1. `get_extra_context(view)` : à surcharger pour injecter n'importe quelle
   donnée métier (stats, objets liés, calculs) dans le contexte de TOUTES
   les vues générées.

2. Les templates par défaut exposent des blocks nommés vides
   (`list_top`, `list_bottom`, `form_top`, `form_bottom`, `detail_extra`)
   qu'on peut remplir en étendant le template par défaut dans un template
   personnalisé, sans dupliquer tout le HTML. Voir README.md.
"""
from __future__ import annotations

import warnings

from django.core.exceptions import PermissionDenied
from django.db import models
from django.forms import modelform_factory
from django.urls import path, reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .mixins import (
    ResourceContextMixin,
    ResourceCreateMessageMixin,
    ResourceDeleteMessageMixin,
    ResourceListContextMixin,
    ResourceLookupMixin,
    ResourceOrderingMixin,
    ResourceSearchMixin,
    ResourceUpdateMessageMixin,
)

# Classes CSS injectées automatiquement sur les widgets du formulaire, selon
# le thème choisi. "plain" utilise des classes neutres (préfixées djr-) que
# l'on peut cibler depuis son propre CSS.
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


class FieldsAllWarning(UserWarning):
    """
    Émis à l'instanciation d'une Resource dont `fields = "__all__"` : le
    formulaire généré exposera tous les champs du modèle, y compris ceux
    ajoutés plus tard (risque de mass assignment). Déclarer explicitement
    les champs autorisés évite cet avertissement.
    """


class Resource:
    """
    Classe de base à hériter pour déclarer une ressource CRUD.

    Attributs de configuration
    ---------------------------
    model (Model)               : modèle Django concerné (obligatoire).
    fields (list | str)         : champs du formulaire ("__all__" par défaut).
    readonly_fields (list)      : champs affichés en lecture seule dans le formulaire.
    list_display (list)         : champs affichés dans la liste (tous les champs du modèle par défaut).
    search_fields (list)        : champs sur lesquels porte la recherche texte (`?q=`).
    ordering_fields (list)      : champs sur lesquels le tri par clic est autorisé (`?sort=&dir=`).
    paginate_by (int)           : nombre d'objets par page (défaut : 20).
    lookup_field (str)          : champ utilisé dans les URLs détail/modification/suppression
                                  pour résoudre un objet ("pk" par défaut ; "slug", "uid",
                                  "uuid", tout champ du modèle — cf. `get_lookup_url()`).
    select_related (list)       : relations ForeignKey à précharger automatiquement (perf).
    prefetch_related (list)     : relations M2M / inverses à précharger automatiquement (perf).
    theme (str)                 : "bootstrap" (défaut) | "tailwind" | "plain".
    auto_form_css (bool)        : injecte automatiquement les classes CSS du thème sur le
                                   formulaire (défaut : True). Mettre à False pour tout
                                   contrôler soi-même (widgets personnalisés, CSS codé en dur).
    template_list/... (str)     : chemins de templates personnalisés (prioritaires sur `theme`).
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

    theme = "bootstrap"
    auto_form_css = True

    # Champ utilisé dans les URLs (détail/modification/suppression) pour
    # résoudre un objet : "pk" (défaut), "slug", "uid", "uuid", "code"...
    # Doit être un champ du modèle. Les templates utilisent sa valeur via
    # `resource.get_lookup_value(objet)`.
    lookup_field = "pk"

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

        # Sécurité (mass assignment) : `fields = "__all__"` expose tous les
        # champs du modèle dans le formulaire — y compris d'éventuels champs
        # sensibles ajoutés plus tard (is_admin, proprietaire, slug interne…).
        # On avertit pour pousser à déclarer explicitement les champs.
        if self.fields == "__all__":
            warnings.warn(
                f"{self.__class__.__name__}.fields = \"__all__\" expose tous les "
                f"champs du modèle {self.model.__name__} dans le formulaire. "
                f"Déclarez explicitement les champs autorisés, ex : "
                f"fields = ['nom', 'prix'].",
                FieldsAllWarning,
                stacklevel=2,
            )

        # Si list_display n'est pas défini explicitement : tous les champs concrets du modèle
        if self.list_display is None:
            self.list_display = [f.name for f in self.model._meta.fields]

    # ------------------------------------------------------------------
    # Contexte métier additionnel (hook d'extension principal)
    # ------------------------------------------------------------------
    def get_extra_context(self, view):
        """
        À surcharger pour injecter des données métier supplémentaires dans
        le contexte de N'IMPORTE QUELLE vue générée (liste, détail,
        formulaire, suppression) — sans avoir à réécrire les vues.

        `view` est l'instance de la vue Django en cours d'exécution : on
        peut y lire `view.request` (utilisateur connecté, GET/POST...),
        et selon le cas `view.object` (détail/update/delete) ou
        `view.object_list` (liste, après filtrage/tri/pagination).

        Exemple :

            class ProduitResource(Resource):
                model = Produit

                def get_extra_context(self, view):
                    return {
                        "valeur_stock_total": sum(
                            p.prix * p.stock for p in Produit.objects.all()
                        ),
                    }

        La donnée `valeur_stock_total` est alors disponible dans TOUS les
        templates (list/detail/form/delete), par exemple dans le block
        `list_top` d'un template personnalisé :

            {{ valeur_stock_total }}
        """
        return {}

    # ------------------------------------------------------------------
    # Résolution des templates selon le thème
    # ------------------------------------------------------------------
    def _theme_template(self, kind: str, explicit: str | None) -> str:
        """
        Résout le chemin du template à utiliser pour `kind`
        ("list", "detail", "form", "confirm_delete").

        Priorité :
        1. Le template explicitement fourni (`template_list`, etc.) — permet
           de surcharger un seul template sans changer de thème.
        2. Le thème "bootstrap" (historique) : `djresource/<kind>.html`.
        3. Tout autre thème : `djresource/<theme>/<kind>.html`.
        """
        if explicit:
            return explicit
        if self.theme == "bootstrap":
            return f"djresource/{kind}.html"
        return f"djresource/{self.theme}/{kind}.html"

    # ------------------------------------------------------------------
    # Formulaire
    # ------------------------------------------------------------------
    def get_form_class(self):
        """
        Construit un ModelForm à partir du modèle, avec :
        - restriction aux `fields` déclarés,
        - classes CSS du thème ajoutées automatiquement à chaque widget
          (sauf si `auto_form_css = False`),
        - champs `readonly_fields` désactivés (non modifiables).
        """
        form_class = modelform_factory(self.model, fields=self.fields)
        readonly_fields = self.readonly_fields
        auto_form_css = self.auto_form_css
        css_classes = THEME_WIDGET_CLASSES.get(self.theme, THEME_WIDGET_CLASSES["plain"])
        original_init = form_class.__init__

        def patched_init(self_form, *args, **kwargs):
            original_init(self_form, *args, **kwargs)
            for field_name, field in self_form.fields.items():
                if auto_form_css:
                    widget_name = field.widget.__class__.__name__
                    if widget_name == "CheckboxInput":
                        css_class = css_classes["checkbox"]
                    elif widget_name in ("Select", "SelectMultiple"):
                        css_class = css_classes["select"]
                    else:
                        css_class = css_classes["default"]
                    existing = field.widget.attrs.get("class", "")
                    field.widget.attrs["class"] = f"{existing} {css_class}".strip()
                if field_name in readonly_fields:
                    field.disabled = True

        form_class.__init__ = patched_init
        return form_class

    # ------------------------------------------------------------------
    # Queryset commun (List / Detail / Update / Delete)
    # ------------------------------------------------------------------
    def get_base_queryset(self):
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
        générées. Par défaut : aucune restriction.

        Ces permissions protègent les pages pleine page (via `dispatch()`)
        ET les composants injectés par les balises `djresource_*` (vérifiées
        dans `_enforce_permissions()` avant la construction du contexte).
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
    # Lookup (résolution d'un objet dans les URLs)
    # ------------------------------------------------------------------
    def get_lookup_url(self):
        """
        Retourne le segment d'URL pour `lookup_field`, avec le bon
        convertisseur Django selon le type du champ :
            "pk"                    -> "<int:pk>"   (ou <uuid:pk> si pk UUID)
            champ SlugField         -> "<slug:slug>"
            champ UUIDField         -> "<uuid:uid>"
            champ Integer/AutoField -> "<int:code>"
            tout autre champ        -> "<str:code>"
        """
        if self.lookup_field == "pk":
            field = self.model._meta.pk
            field_name = "pk"
        else:
            field = self.model._meta.get_field(self.lookup_field)
            field_name = self.lookup_field
        if isinstance(field, models.UUIDField):
            return f"<uuid:{field_name}>"
        if isinstance(field, models.SlugField):
            return f"<slug:{field_name}>"
        if isinstance(field, (models.IntegerField, models.AutoField)):
            return f"<int:{field_name}>"
        return f"<str:{field_name}>"

    def get_lookup_value(self, obj):
        """Valeur du champ de lookup pour un objet (ex: obj.slug, obj.uid)."""
        return getattr(obj, self.lookup_field)

    # ------------------------------------------------------------------
    # Contextes "partiels" (injection dans une page personnalisée)
    # ------------------------------------------------------------------
    # Chaque méthode instancie la CBV générée correspondante et lui fait
    # produire son contexte via get_context_data(). On réutilise ainsi à
    # l'identique toute la chaîne des mixins (contexte commun, recherche,
    # tri, pagination, formulaire, extra_context) : une page personnalisée
    # qui injecte un composant affiche EXACTEMENT les mêmes données et
    # métadonnées que la vue pleine page.
    def _new_view(self, view_cls, request, **kwargs):
        """Instancie une CBV générée et la prépare avec la requête courante."""
        self._enforce_permissions(view_cls, request, **kwargs)
        view = view_cls()
        view.setup(request, **kwargs)
        return view

    def _enforce_permissions(self, view_cls, request, **kwargs):
        """
        Applique les mixins de permissions (`get_permissions()`) à la
        requête, comme le ferait `dispatch()` sur une page pleine page.

        Les permissions Django (LoginRequiredMixin, PermissionRequiredMixin,
        mixins custom...) sont implémentées dans `dispatch()`. Hors requête
        HTTP, le rendu d'un partiel n'appelle jamais `dispatch()` — ce qui
        laisserait fuiter des données protégées via une balise
        `{% djresource_list %}` sur une page publique.

        On instancie donc la vue avec des handlers HTTP neutralisés et on
        lance son `dispatch()` : si la réponse retournée n'est pas le
        marqueur interne, c'est que la permission a été refusée
        (redirection login / 403) → on lève `PermissionDenied`.
        """
        permissions = self.get_permissions()
        if not permissions:
            return

        class _PermissionCheckView(view_cls):
            _ok = object()

            def _neutralize(self, request, *args, **kwargs):
                return self._ok

            get = post = head = put = patch = delete = options = trace = _neutralize

        check_view = _PermissionCheckView()
        check_view.setup(request, **kwargs)
        response = check_view.dispatch(request, **kwargs)
        if response is not _PermissionCheckView._ok:
            raise PermissionDenied

    def get_list_context(self, request):
        """
        Contexte de la vue "liste" (recherche, tri, pagination, list_display),
        prêt à être injecté n'importe où via la balise `djresource_list`.
        """
        view = self._new_view(self.get_list_view(), request)
        view.object_list = view.get_queryset()
        return view.get_context_data()

    def get_form_context(self, request, lookup_value=None):
        """
        Contexte de la vue "formulaire" : création si `lookup_value` est
        omis, modification sinon (résolu via `lookup_field`). Contient la
        clé `form` et `object` (le cas échéant). Sert la balise
        `djresource_form`.
        """
        if lookup_value is not None:
            view = self._new_view(self.get_update_view(), request, **{self.lookup_field: lookup_value})
            view.object = view.get_object()
        else:
            view = self._new_view(self.get_create_view(), request)
            view.object = None  # SingleObjectMixin accède à self.object
        context = view.get_context_data()
        # Filet de sécurité : FormMixin fournit normalement la clé "form",
        # on s'assure qu'elle est toujours présente pour le template partiel.
        if "form" not in context:
            context["form"] = view.get_form()
        return context

    def get_detail_context(self, request, lookup_value):
        """
        Contexte de la vue "détail" d'un objet précis, pour la balise
        `djresource_detail`.
        """
        view = self._new_view(self.get_detail_view(), request, **{self.lookup_field: lookup_value})
        view.object = view.get_object()
        return view.get_context_data()

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
        urls.py via `include(MaResource().urls())`.
        """
        lookup = self.get_lookup_url()
        return [
            path("", self.get_list_view().as_view(), name=self.url_name("list")),
            path("nouveau/", self.get_create_view().as_view(), name=self.url_name("create")),
            path(f"{lookup}/", self.get_detail_view().as_view(), name=self.url_name("detail")),
            path(f"{lookup}/modifier/", self.get_update_view().as_view(), name=self.url_name("update")),
            path(f"{lookup}/supprimer/", self.get_delete_view().as_view(), name=self.url_name("delete")),
        ]
