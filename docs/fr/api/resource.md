# Classe Resource

C'est le cœur de la bibliothèque. Une sous-classe de `Resource` déclare un modèle
Django + des attributs de configuration ; les vues CRUD, le formulaire et
les routes sont générés automatiquement à l'exécution.

## Exemple minimal

```python
from djresource.resource import Resource
from .models import Produit

class ProduitResource(Resource):
    model = Produit
    list_display = ["nom", "prix", "stock"]
    search_fields = ["nom"]
```

## Référence

::: djresource.resource.Resource

## Défauts de sécurité

Les ressources générées exigent une authentification, sauf si
`public = True` est défini explicitement. La valeur par défaut
`fields = []` signifie qu'aucun champ du modèle n'est modifiable ; déclarez
une liste blanche explicite pour chaque formulaire de création/modification.
L'ancienne valeur `fields = "__all__"` reste compatible mais émet
`FieldsAllWarning`.

Surchargez `scope_queryset(queryset, request)` pour isoler les propriétaires
ou les tenants. `get_queryset(request)` applique ce périmètre au queryset de
base et est utilisé pour la liste, le détail, la modification, la
suppression et les contextes des composants injectés.

## Résolution des templates

::: djresource.resource.Resource._theme_template

## Lookup des objets (`lookup_field`)

::: djresource.resource.Resource.get_lookup_url
::: djresource.resource.Resource.get_lookup_value

## Contexte de composant (balises d'injection)

::: djresource.resource.Resource.get_list_context
::: djresource.resource.Resource.get_form_context
::: djresource.resource.Resource.get_detail_context
