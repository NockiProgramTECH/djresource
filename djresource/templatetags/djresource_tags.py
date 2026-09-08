"""
djresource.templatetags.djresource_tags
========================================

Filtres et balises de template du framework.

Deux familles de balises :

1. `djresource_list` / `djresource_form` / `djresource_detail` : rendent
   un composant HTML tout fait (thème choisi) directement dans votre page.

2. `djresource_list_data` / `djresource_form_data` / `djresource_detail_data` :
   ne rendent AUCUN HTML — elles renvoient les données brutes via
   `{% ... as variable %}`, pour un affichage 100% libre.

SÉCURITÉ : `resource_path` doit TOUJOURS être une chaîne codée en dur
dans votre template, jamais une valeur construite depuis une donnée
utilisateur (GET/POST/session) — voir docstring de `_resolve_resource`.
"""
from django import template
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

register = template.Library()


# ---------------------------------------------------------------------
# Filtres (affichage de champs dynamiques, y compris les relations)
# ---------------------------------------------------------------------
def _is_related_manager(value):
    """Détecte un manager de relation (ManyToMany, ou ForeignKey inversée)."""
    return hasattr(value, "all") and callable(getattr(value, "all", None))


@register.filter(name="get_attr")
def get_attr(obj, attr_name):
    """
    Retourne la valeur d'un attribut/champ dynamique d'un objet, prête à
    afficher — y compris pour une relation :
    - ForeignKey / OneToOneField : affiche str(objet lié) (comportement
      normal de Django, rien de spécial à faire ici).
    - ManyToManyField ou relation inversée (FK depuis un autre modèle) :
      affiche la liste des objets liés, séparés par des virgules.

    Usage dans un template : {{ object|get_attr:field }}
    où `field` est une chaîne (ex: "nom", "categorie", "tags") venant de
    `list_display`.
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
    Retourne la liste des champs (label lisible, valeur) d'une instance de
    modèle, utilisée par le template de détail pour afficher tous les
    champs sans connaître leurs noms à l'avance.

    Couvre :
    - les champs concrets (y compris ForeignKey/OneToOneField, affichés
      via leur __str__ automatiquement),
    - les champs à choix (`choices=...`), affichés via get_<field>_display(),
    - les champs ManyToManyField (absents de `_meta.fields` en Django,
      donc traités séparément), affichés en liste séparée par des virgules.
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
# Résolution sécurisée d'une Resource depuis un chemin Python
# ---------------------------------------------------------------------
def _resolve_resource(resource_path):
    """
    Importe et instancie une Resource à partir de son chemin Python complet.

    SÉCURITÉ : `resource_path` doit toujours être une chaîne codée en dur
    dans votre template (ex: "produits.resources.ProduitResource"), jamais
    une valeur construite depuis une donnée utilisateur — un chemin
    contrôlé par l'utilisateur permettrait d'importer et d'instancier
    n'importe quelle classe Python accessible dans le projet. Une
    vérification (`issubclass(..., Resource)`) empêche d'utiliser une
    classe qui n'est pas une Resource, mais ne protège pas contre un
    chemin dynamique malveillant.
    """
    from ..resource import Resource  # import différé : évite un import circulaire (remonte au package parent djresource, PAS djresource.templatetags)

    try:
        resource_class = import_string(resource_path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"djresource : impossible d'importer '{resource_path}'. "
            "Vérifiez le chemin (format 'module.sous_module.NomDeClasse')."
        ) from exc

    if not (isinstance(resource_class, type) and issubclass(resource_class, Resource)):
        raise ImproperlyConfigured(
            f"djresource : '{resource_path}' n'est pas une sous-classe de "
            "djresource.resource.Resource."
        )
    return resource_class()


# ---------------------------------------------------------------------
# Balises "composant rendu" (HTML tout fait, thème choisi)
# ---------------------------------------------------------------------
@register.simple_tag(takes_context=True)
def djresource_list(context, resource_path):
    """
    Injecte le composant "liste" (tableau, thème choisi) tout rendu dans
    le template courant.

    Usage :
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
    Injecte le composant "formulaire" tout rendu (création si `lookup`
    omis, modification sinon) dans le template courant.

    `lookup` est la valeur du `lookup_field` de la Resource ("pk" par
    défaut, donc `produit.pk` dans le cas courant — ou `produit.slug` si
    la Resource définit `lookup_field = "slug"`, etc.)

    Usage :
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
    Injecte le composant "détail" tout rendu d'un objet précis dans le
    template courant. `lookup` = valeur du `lookup_field` de la Resource.

    Usage :
        {% djresource_detail "produits.resources.ProduitResource" produit.pk %}
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    detail_context = resource.get_detail_context(request, lookup)
    template_name = resource._theme_template("detail_partial", None)
    return mark_safe(render_to_string(template_name, detail_context, request=request))


# ---------------------------------------------------------------------
# Balises "données brutes" (aucun HTML — affichage 100% libre)
# ---------------------------------------------------------------------
@register.simple_tag(takes_context=True)
def djresource_list_data(context, resource_path):
    """
    Calcule les données de la liste SANS rendre aucun HTML. À utiliser
    avec `as` pour construire votre propre affichage (cartes, grille...).

    Usage :
        {% djresource_list_data "produits.resources.ProduitResource" as produits %}
        {% for produit in produits.object_list %}
          <a href="{% url produits.url_detail produit.pk %}">{{ produit.nom }}</a>
        {% endfor %}

    Note : utilisez `produit.pk` (ou l'attribut correspondant à
    `lookup_field` si vous l'avez personnalisé) dans les URLs, pas un
    identifiant arbitraire.
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    return resource.get_list_context(request)


@register.simple_tag(takes_context=True)
def djresource_form_data(context, resource_path, lookup=None):
    """
    Comme `djresource_list_data`, pour un formulaire (création si `lookup`
    omis, modification sinon).

    Usage :
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
    Comme `djresource_list_data`, pour le détail d'un objet précis.

    Usage :
        {% djresource_detail_data "produits.resources.ProduitResource" produit_id as d %}
        <h1>{{ d.object.nom }}</h1>
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    return resource.get_detail_context(request, lookup)
