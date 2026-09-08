# Balises et filtres de template

Le module `djresource/templatetags/djresource_tags.py` fournit des filtres
pour afficher des champs dynamiques et des balises pour injecter un
composant CRUD dans n'importe quelle page.

## Chargement

```django
{% load djresource_tags %}
```

## Filtres

### `get_attr`

Retourne la valeur d'un attribut/champ dynamique d'un objet (nom venant de
`list_display` par exemple). Appelle les callables automatiquement.

```django
{{ object|get_attr:field }}
```

::: djresource.templatetags.djresource_tags.get_attr

### `get_fields_display`

Retourne la liste des champs (label lisible, valeur) d'une instance de
modèle — utilisée par la vue détail. Gère les champs `choices` via
`get_<field>_display()`.

::: djresource.templatetags.djresource_tags.get_fields_display

## Balises d'injection de composants

Ces balises rendent **uniquement** le composant (liste, formulaire, détail),
sans structure de page : à placer dans une page que vous avez déjà mise en
page.

!!! note
    Elles nécessitent le context processor
    `django.template.context_processors.request`.

### `djresource_list`

```django
{% djresource_list "produits.resources.ProduitResource" %}
```

::: djresource.templatetags.djresource_tags.djresource_list

### `djresource_form`

Création si `lookup` est omis, modification sinon. `lookup` est la valeur du
champ `lookup_field` de la Resource (pk par défaut) :

```django
{% djresource_form "produits.resources.ProduitResource" %}
{% djresource_form "produits.resources.ProduitResource" produit.slug %}
```

Options : `template=` (surcharge le partiel), `cle=valeur` (données
fusionnées dans le contexte du partiel).

::: djresource.templatetags.djresource_tags.djresource_form

### `djresource_detail`

`lookup` est la valeur du champ `lookup_field` de la Resource (pk par
défaut) :

```django
{% djresource_detail "produits.resources.ProduitResource" produit.slug %}
```

Options identiques à `djresource_form`.

::: djresource.templatetags.djresource_tags.djresource_detail
