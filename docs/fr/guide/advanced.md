# Fonctionnalités avancées

## Permissions

Par défaut, les vues générées exigent une authentification. Définissez
explicitement `public = True` pour rendre une ressource publique. Vous pouvez
ajouter des mixins de permission en surchargeant `get_permissions()`.

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class ProduitResource(Resource):
    model = Produit

    def get_permissions(self):
        return [
            LoginRequiredMixin,
            # PermissionRequiredMixin (nécessite permission_required en attribut)
        ]
```

La même chaîne de permissions s'applique aux composants injectés, y compris
`UserPassesTestMixin` et les mixins de permission métier personnalisés.

!!! important "Les partiels sont protégés aussi"
    Les permissions s'appliquent aux pages pleine page **ET** aux composants
    injectés par les balises `{% djresource_list %}` etc. : avant de
    construire le contexte d'un partiel, la bibliothèque simule le
    `dispatch()` de la vue concernée et lève `PermissionDenied` si la
    requête n'est pas autorisée. Un visiteur anonyme ne peut donc pas lire
    les données d'une Resource protégée en l'injectant dans une page
    publique.

!!! tip "Ordre du MRO"
    Les mixins sont placés **avant** la vue générique Django dans le tuple
    `bases`. Toute méthode appelée par Django (`dispatch`, `get_queryset`,
    `get_context_data`, `form_valid`…) passe donc d'abord par vos mixins.

## Optimisation des requêtes

Évitez le problème N+1 sur les relations :

```python
class CommandeResource(Resource):
    model = Commande
    select_related = ["client", "livreur"]
    prefetch_related = ["articles"]
```

- `select_related` : ForeignKey / OneToOne (jointure SQL).
- `prefetch_related` : ManyToMany et relations inverses.

## Filtre commun sur le queryset

Surchargez `scope_queryset()` pour isoler les objets selon la requête
courante. Il s'applique à **toutes** les vues (List, Detail, Update, Delete)
et aux contextes injectés :

```python
class ProduitResource(Resource):
    model = Produit

    def scope_queryset(self, queryset, request):
        return queryset.filter(owner=request.user)
```

`get_base_queryset()` reste le hook du queryset de base du modèle ;
`get_queryset(request)` retourne le queryset complètement isolé.

## Changer le champ de lookup des URLs

Par défaut, les URLs de détail, modification et suppression identifient un
objet par son pk (`<int:pk>`). Grâce à l'attribut `lookup_field`, vous pouvez
utiliser n'importe quel **autre champ unique** du modèle — typiquement un
`slug`, un `uid`, une référence… :

```python
class ArticleResource(Resource):
    model = Article
    lookup_field = "slug"    # au lieu du pk
```

Les URLs générées deviennent alors :

- `/articles/riz-local/` (détail),
- `/articles/riz-local/modifier/` (modification),
- `/articles/riz-local/supprimer/` (suppression).

La bibliothèque choisit le bon convertisseur d'URL Django selon le type du
champ (`Resource.get_lookup_url()`) :

| Champ | Convertisseur | Exemple |
|---|---|---|
| `IntegerField` / `AutoField` (pk) | `<int:nom>` | `/produits/42/` |
| `SlugField` | `<slug:nom>` | `/articles/riz-local/` |
| `UUIDField` | `<uuid:nom>` | `/commandes/550e8400-…/` |
| tout autre champ | `<str:nom>` | `/codes/REF-2026/` |

!!! warning "Champ unique requis"
    Le champ doit être **unique** : la résolution d'objet
    (`ResourceLookupMixin.get_object`) utilise
    `get_object_or_404(queryset, lookup_field=valeur)`. Deux objets partageant
    la même valeur lèveraient une erreur `MultipleObjectsReturned`.

Les templates s'adaptent automatiquement (les liens de liste, détail et
formulaire utilisent la valeur de `resource.lookup_field`, jamais `pk` en
dur). Voir `ArticleResource` et `ArticleSlugLookupTests` dans la suite de
tests (`tests/`) pour un exemple complet.

## Injecter un composant CRUD dans n'importe quelle page

Les balises `djresource_list`, `djresource_form` et `djresource_detail`
permettent d'afficher un composant CRUD **dans une page que vous avez déjà
codée**, avec votre propre structure autour. Elles ne rendent **que** le
composant (pas de `<html>`, pas de navbar).

```html
{% load djresource_tags %}

<h1>Mon tableau de bord</h1>
{% djresource_list "produits.resources.ProduitResource" %}
```

```html
{% load djresource_tags %}
{% djresource_form "produits.resources.ProduitResource" %}              {# création #}
{% djresource_form "produits.resources.ProduitResource" produit.slug %} {# modification #}
```

```html
{% load djresource_tags %}
{% djresource_detail "produits.resources.ProduitResource" produit.slug %}
```

Le 2ᵉ argument des balises `djresource_form` / `djresource_detail` est la
valeur du champ `lookup_field` de la Resource : `produit.pk` (par défaut),
`produit.slug`, `produit.uid`… selon votre configuration.

### Options des balises

- **`template=`** : surcharge le template partiel utilisé pour le rendu
  (par défaut, le partiel du thème de la Resource).
  ```html
  {% djresource_list "..." template="monapp/_tableau.html" %}
  ```
- **`cle=valeur`** : données supplémentaires fusionnées dans le contexte
  du partiel, accessibles dans le template comme n'importe quelle variable.
  ```html
  {% djresource_list "..." titre="Promos du jour" %}
  ```

### Contenu du composant injecté

Les partiels (`*_partial.html`, déclinés par thème) ne contiennent ni `<html>`,
ni navbar : uniquement le composant. Leur contexte est le même que celui de
la vue pleine page correspondante : `resource`, `verbose_name`, les URL
nommées (`url_list`, `url_create`, `url_update`, `url_delete`),
`object_list`, `page_obj`, `list_display`, et les données de
`get_extra_context()`. Les partiels exposent les mêmes blocs d'extension
que les templates pleine page : `list_top`, `list_bottom`, `form_top`,
`form_bottom`, `detail_extra`.

!!! note "Contexte"
    Ces balises nécessitent le context processor
    `django.template.context_processors.request` (activé par défaut).

## Messages de succès personnalisés

Les messages utilisent `django.contrib.messages`. Personnalisez-les :

```python
class ProduitResource(Resource):
    model = Produit
    success_message_create = "Le produit %(name)s a bien été créé."
    success_message_update = "Le produit %(name)s a bien été modifié."
    success_message_delete = "%(name)s a bien été supprimé."
```

`%(name)s` est remplacé par le `verbose_name` du modèle (create/update) ou
par `str(objet)` (delete).

## Variables de contexte disponibles

`ResourceContextMixin` injecte dans **tous** les templates :

| Variable | Contenu |
|---|---|
| `resource` | L'instance de la ressource courante |
| `verbose_name` / `verbose_name_plural` | Libellés du modèle |
| `url_list` / `url_create` / `url_detail` / `url_update` / `url_delete` | Noms de routes (pour `{% url %}`) |
| `list_display` | Colonnes de la liste (vue liste) |
| `search_query` / `search_enabled` | État de la recherche (vue liste) |
| `current_sort` / `current_dir` | État du tri (vue liste) |

!!! warning "Noms de routes dynamiques"
    Les templates par défaut n'appellent jamais `{% url 'produit_list' %}` :
    ils utilisent les variables `url_list`, etc., car le nom exact de la
    ressource n'est connu qu'au moment de l'inclusion dans `urls.py`.
