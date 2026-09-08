"""
djresource.mixins
==================

Mixins utilisés pour composer dynamiquement les vues générées par `Resource`.

Chaque mixin ne fait qu'une seule chose et respecte la chaîne `super()`,
afin de pouvoir être librement combiné dans `Resource.get_*_view()` sans
écraser le comportement des autres mixins (voir resource.py).

ORDRE DES MIXINS DANS LES BASES (important, ne pas changer sans comprendre) :
Pour Create/Update, l'ordre est :
    ResourceContextMixin, ResourceFormActionMixin, ResourceCreateMessageMixin,
    ResourceInlineFormsetMixin, ResourceSaveHooksMixin, *permissions, CreateView
Le "form_valid" le plus extérieur (message) enveloppe le formset, qui
enveloppe la sauvegarde réelle (hooks). Chaque mixin appelle super() pour
déléguer vers le suivant ; l'ordre dans le tuple de bases EST l'ordre
d'exécution (le premier listé s'exécute en premier).
"""
from django.contrib import messages
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse


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


class ResourceFormActionMixin:
    """
    Calcule `form_action_url`, utilisé par le template de formulaire pour
    poster explicitement vers l'URL de création/modification générée par
    le framework — nécessaire pour que le formulaire fonctionne aussi
    lorsqu'il est injecté (via `{% djresource_form %}`) dans une page qui
    n'est pas elle-même la vue de création/modification.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource = self.resource
        obj = getattr(self, "object", None)
        if obj is not None and obj.pk:
            lookup_value = resource.get_lookup_value(obj)
            context["form_action_url"] = reverse(resource.url_name("update"), args=[lookup_value])
        else:
            context["form_action_url"] = reverse(resource.url_name("create"))
        return context


class ResourceLookupMixin:
    """
    Récupère l'objet via `Resource.lookup_field` ("pk" par défaut, mais
    peut être n'importe quel champ unique du modèle : "slug", "name"...).
    """

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        resource = self.resource
        lookup_value = self.kwargs[resource.lookup_url_kwarg]
        return get_object_or_404(queryset, **{resource.lookup_field: lookup_value})


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
    aux champs déclarés dans `ordering_fields`.
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


class ResourceFilterMixin:
    """
    Filtre la liste via `?champ=valeur`, restreint aux champs déclarés
    dans `list_filter` de la Resource (booléens et champs à `choices`
    typiquement). Les filtres se cumulent entre eux et avec la recherche
    `?q=` (ET logique). La validation est déléguée à la Resource
    (`get_active_list_filters`), partagée avec `get_list_context()`.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.GET if getattr(self, "request", None) else {}
        return self.resource.apply_list_filters(qs, params)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET if getattr(self, "request", None) else {}
        context["filters_enabled"] = bool(self.resource.list_filter)
        context["list_filters"] = self.resource.get_list_filter_options(params)
        return context


# ---------------------------------------------------------------------
# Sauvegarde : hooks de logique métier (before_save/after_save/clean)
# ---------------------------------------------------------------------
class ResourceSaveHooksMixin:
    """
    Remplace le form_valid() par défaut de Create/UpdateView pour appeler
    les hooks de logique métier de la Resource (`clean`, `before_save`,
    `after_save`) autour de la sauvegarde.

    Utilise `form.save(commit=False)` pour pouvoir intervenir avant
    l'écriture en base, puis appelle explicitement `save_m2m()` (requis
    par Django dès qu'on utilise `commit=False` sur un ModelForm ayant
    des champs ManyToMany — sans ça, les relations M2M ne seraient
    jamais enregistrées).
    """

    def form_valid(self, form):
        resource = self.resource
        is_new = form.instance.pk is None
        instance = form.save(commit=False)

        try:
            resource.clean(instance, self.request)
        except DjangoValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)

        resource.before_save(instance, self.request, is_new)
        instance.save()
        if hasattr(form, "save_m2m"):
            form.save_m2m()
        resource.after_save(instance, self.request, is_new)

        self.object = instance
        return HttpResponseRedirect(self.get_success_url())


class ResourceDeleteHooksMixin:
    """
    Appelle `Resource.before_delete()` / `after_delete()` autour de la
    suppression. `before_delete` peut lever `ValidationError` pour
    empêcher la suppression (message d'erreur affiché, objet conservé).
    """

    def form_valid(self, form):
        resource = self.resource
        instance = self.object
        try:
            resource.before_delete(instance, self.request)
        except DjangoValidationError as exc:
            messages.error(self.request, str(exc))
            return HttpResponseRedirect(self.request.path)

        response = super().form_valid(form)  # exécute la suppression réelle (Django)
        resource.after_delete(instance, self.request)
        return response


# ---------------------------------------------------------------------
# Formsets inline (édition d'objets liés dans le même formulaire)
# ---------------------------------------------------------------------
class ResourceInlineFormsetMixin:
    """
    Gère les formsets déclarés via `Resource.inlines` : instanciation
    (GET), validation (POST), et sauvegarde APRÈS la sauvegarde de
    l'objet parent (nécessaire : les lignes liées ont besoin du `pk` du
    parent, qui n'existe qu'une fois celui-ci enregistré).

    Doit être placé AVANT `ResourceSaveHooksMixin` dans les bases (donc
    son `form_valid` s'exécute en premier, et son `super().form_valid()`
    délègue la sauvegarde du parent au mixin suivant).
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "inline_formsets" not in context:
            context["inline_formsets"] = self._build_formsets(
                instance=getattr(self, "object", None), data=None, files=None
            )
        return context

    def _build_formsets(self, instance, data, files):
        formsets = []
        for inline in self.resource.inlines:
            formset_class = inline.get_formset_class(self.resource.model)
            if data is not None:
                formsets.append(formset_class(data, files, instance=instance))
            else:
                formsets.append(formset_class(instance=instance))
        return formsets

    def form_valid(self, form):
        if not self.resource.inlines:
            return super().form_valid(form)

        formsets = self._build_formsets(
            instance=form.instance, data=self.request.POST, files=self.request.FILES
        )
        if not all(fs.is_valid() for fs in formsets):
            return self.render_to_response(
                self.get_context_data(form=form, inline_formsets=formsets)
            )

        # Sauvegarde le parent d'abord (délègue à ResourceSaveHooksMixin,
        # qui appelle avant/après-hooks) : self.object a un pk après ça.
        response = super().form_valid(form)

        for formset in formsets:
            formset.instance = self.object
            formset.save()

        return response


# ---------------------------------------------------------------------
# Messages de succès (Create / Update / Delete)
# ---------------------------------------------------------------------
class ResourceCreateMessageMixin:
    """
    Ajoute un message de succès après création. Ne l'ajoute que si la
    réponse est une redirection : si un formset inline est invalide,
    form_valid() peut renvoyer un simple ré-affichage du formulaire (200)
    plutôt qu'une redirection — dans ce cas, pas de faux message de succès.
    """

    def form_valid(self, form):
        response = super().form_valid(form)
        if isinstance(response, HttpResponseRedirect):
            messages.success(
                self.request,
                self.resource.success_message_create % {"name": self.resource.verbose_name},
            )
        return response


class ResourceUpdateMessageMixin:
    """Ajoute un message de succès après modification (même garde qu'au-dessus)."""

    def form_valid(self, form):
        response = super().form_valid(form)
        if isinstance(response, HttpResponseRedirect):
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
