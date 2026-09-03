"""
djresource.templatetags.djresource_tags
========================================

Filtres et balises de template de la bibliothèque.

Les balises `djresource_list`, `djresource_form`, `djresource_detail`
permettent d'injecter un composant CRUD (tableau de liste, formulaire,
détail) directement dans N'IMPORTE QUEL template — y compris une page
que vous avez déjà codée vous-même, avec votre propre structure autour.
Elles ne rendent QUE le composant (pas de <html>, pas de navbar) : les
données injectées restent les vôtres à mettre en page comme vous voulez.
"""
from django import template
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

register = template.Library()


# ---------------------------------------------------------------------
# Filtres (affichage de champs dynamiques)
# ---------------------------------------------------------------------
@register.filter(name="get_attr")
def get_attr(obj, attr_name):
    """
    Retourne la valeur d'un attribut/champ dynamique d'un objet.

    Usage dans un template : {{ object|get_attr:field }}
    où `field` est une chaîne (ex: "nom", "prix") venant de `list_display`.
    """
    value = getattr(obj, attr_name, "")
    if callable(value):
        value = value()
    return value


@register.filter(name="get_fields_display")
def get_fields_display(obj):
    """
    Retourne la liste des champs (label lisible, valeur) d'une instance de
    modèle, utilisée par le template de détail pour afficher tous les
    champs sans connaître leurs noms à l'avance.

    Gère aussi les champs à choix (`choices=...`) en affichant le libellé
    via get_<field>_display() plutôt que la valeur brute stockée en base.
    """
    result = []
    for f in obj._meta.fields:
        value = getattr(obj, f.name)
        display_method_name = f"get_{f.name}_display"
        if hasattr(obj, display_method_name):
            value = getattr(obj, display_method_name)()
        result.append({"label": f.verbose_name, "value": value})
    return result


# ---------------------------------------------------------------------
# Balises d'injection de composants CRUD dans une page personnalisée
# ---------------------------------------------------------------------
def _resolve_resource(resource_path):
    """Importe et instancie une Resource à partir de son chemin Python complet."""
    resource_class = import_string(resource_path)
    return resource_class()


@register.simple_tag(takes_context=True)
def djresource_list(context, resource_path, template=None, **kwargs):
    """
    Injecte le composant "liste" (recherche + tri + pagination) d'une
    Resource directement dans le template courant.

    Usage :
        {% load djresource_tags %}
        {% djresource_list "produits.resources.ProduitResource" %}

    `resource_path` est le chemin Python complet vers la classe Resource
    ("<module>.<Classe>"). Nécessite que le context processor
    "django.template.context_processors.request" soit activé (c'est le
    cas par défaut dans un projet Django standard).

    Options :
    - `template="monapp/_liste.html"` : surcharge le template partiel
      utilisé (sinon le partiel du thème de la Resource).
    - `cle=valeur` : données supplémentaires fusionnées dans le contexte
      du partiel (ex: `{% djresource_list "..." mon_message="coucou" %}`).
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    list_context = resource.get_list_context(request)
    list_context.update(kwargs)
    template_name = template or resource._theme_template("list_partial", None)
    return mark_safe(render_to_string(template_name, list_context, request=request))


@register.simple_tag(takes_context=True)
def djresource_form(context, resource_path, lookup=None, template=None, **kwargs):
    """
    Injecte le composant "formulaire" (création si `lookup` est omis,
    modification sinon) d'une Resource dans le template courant. Le
    formulaire soumet directement vers l'URL générée par la bibliothèque
    (création/modification), la page englobante n'a rien à gérer.

    Usage :
        {% djresource_form "produits.resources.ProduitResource" %}
        {% djresource_form "produits.resources.ProduitResource" produit.slug %}

    `lookup` est la valeur du champ de lookup de la Resource
    (`resource.lookup_field`, par défaut le pk) : produit.pk, produit.slug,
    produit.uid... Mêmes options que `djresource_list` (`template=`,
    `cle=valeur`).
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    form_context = resource.get_form_context(request, lookup_value=lookup)
    form_context.update(kwargs)
    template_name = template or resource._theme_template("form_partial", None)
    return mark_safe(render_to_string(template_name, form_context, request=request))


@register.simple_tag(takes_context=True)
def djresource_detail(context, resource_path, lookup, template=None, **kwargs):
    """
    Injecte le composant "détail" d'un objet précis dans le template courant.

    Usage :
        {% djresource_detail "produits.resources.ProduitResource" produit.slug %}

    `lookup` est la valeur du champ de lookup de la Resource
    (`resource.lookup_field`, par défaut le pk). Mêmes options que
    `djresource_list` (`template=`, `cle=valeur`).
    """
    request = context.get("request")
    resource = _resolve_resource(resource_path)
    detail_context = resource.get_detail_context(request, lookup)
    detail_context.update(kwargs)
    template_name = template or resource._theme_template("detail_partial", None)
    return mark_safe(render_to_string(template_name, detail_context, request=request))
