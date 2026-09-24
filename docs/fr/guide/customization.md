# Personnalisation

Un CRUD généré affiche rarement **que** les champs du modèle : on veut
souvent une information calculée, un bandeau, un bouton supplémentaire.
Deux mécanismes complémentaires existent, **sans jamais toucher au code des
vues**.

## 1. Injecter des données métier : `get_extra_context()`

À surcharger dans votre `Resource`. Le résultat est fusionné automatiquement
dans le contexte de **toutes** les vues générées (liste, détail, formulaire,
suppression).

```python
class ProduitResource(Resource):
    model = Produit

    def get_extra_context(self, view):
        return {
            "valeur_stock_total": sum(
                p.prix * p.stock for p in Produit.objects.all()
            ),
        }
```

`view` est l'instance de la vue en cours : on peut y lire `view.request`
(utilisateur connecté, paramètres GET…), et selon le cas `view.object`
(détail/update/delete) ou `view.object_list` (liste, déjà filtrée/triée).

## 2. Afficher ces données : les blocs d'extension

Les templates par défaut (des 3 thèmes) exposent des blocs Django vides à
des emplacements utiles :

| Template | Blocs disponibles |
|---|---|
| `list.html` | `list_header_actions` (à côté du bouton "+ Ajouter"), `list_top` (bandeau sous le titre), `list_bottom` (sous le tableau) |
| `form.html` | `form_top` (avant le formulaire), `form_bottom` (après) |
| `detail.html` | `detail_extra` (après le tableau des champs) |

Créez un template **dans votre propre application** qui étend le template
par défaut du thème utilisé et remplit le bloc voulu :

```html
{# produits/templates/produits/liste_produits.html #}
{% extends "djresource/list.html" %}
{# ou djresource/tailwind/list.html, djresource/plain/list.html #}

{% block list_top %}
<div class="alert alert-info">
    Valeur totale du stock : {{ valeur_stock_total }} FCFA
</div>
{% endblock %}
```

Puis pointez votre ressource vers ce template :

```python
class ProduitResource(Resource):
    model = Produit
    template_list = "produits/liste_produits.html"

    def get_extra_context(self, view):
        return {
            "valeur_stock_total": sum(
                p.prix * p.stock for p in Produit.objects.all()
            ),
        }
```

## Filtrer la liste : `list_filter`

```python
class ArticleResource(Resource):
    model = Article
    list_filter = ["actif", "etat"]   # booléen, champ à choices...
```

La page de liste affiche alors une liste déroulante par champ
(`?actif=1`, `?etat=brouillon`…), cumulable avec la recherche `?q=`.
Les valeurs invalides sont ignorées (pas de filtre).

## Surcharger un template en entier

Si les blocs ne suffisent pas, `template_list`, `template_detail`,
`template_form` et `template_delete` peuvent pointer vers un template
totalement autonome, qui n'étend rien de la bibliothèque :

```python
class ProduitResource(Resource):
    model = Produit
    template_list = "produits/ma_liste_perso.html"
```

## Tableau récapitulatif des attributs

| Attribut | Rôle |
|---|---|
| `model` | Modèle Django (**obligatoire**) |
| `fields` | Liste blanche des champs du formulaire (vide par défaut) |
| `readonly_fields` | Champs affichés mais non modifiables |
| `list_display` | Colonnes affichées dans la liste |
| `search_fields` | Champs concernés par la recherche texte |
| `ordering_fields` | Champs sur lesquels le tri par clic est autorisé |
| `list_filter` | Champs filtrables via `?champ=valeur` (booléens, champs à `choices`) |
| `paginate_by` | Nombre d'objets par page (défaut : 20) |
| `lookup_field` | Champ utilisé dans les URLs détail/modification/suppression (`"pk"` par défaut, ou `"slug"`, `"uid"`, etc.) |
| `select_related` / `prefetch_related` | Optimisation des requêtes sur les relations |
| `theme` | `"bootstrap"` (défaut) \| `"tailwind"` \| `"plain"` \| thème custom |
| `auto_form_css` | Injection auto des classes CSS du thème sur le formulaire (défaut : `True`) |
| `template_list` / `template_detail` / `template_form` / `template_delete` | Surcharge d'un template précis (prioritaire sur `theme`) |
| `get_extra_context(view)` | Injecte des données métier supplémentaires dans le contexte de toutes les vues |
| `public` | Active explicitement l'accès sans authentification |
| `get_permissions()` | Mixins de permission supplémentaires |
| `scope_queryset(queryset, request)` / `get_queryset(request)` | Isolation des objets selon la requête |
| `get_base_queryset()` | Queryset de base avec préchargement des relations |

!!! danger "Sécurité : écriture interdite par défaut"
    Le défaut `fields = []` n'expose aucun champ du modèle dans le formulaire.
    Déclarez toujours la liste explicite des champs modifiables :

    ```python
    class ProduitResource(Resource):
        model = Produit
        fields = ["nom", "prix", "stock"]   # uniquement ces champs
    ```

    La valeur historique `fields = "__all__"` reste disponible pour
    compatibilité et émet un `FieldsAllWarning`; ne l'utilisez pas pour des
    modèles sensibles.
