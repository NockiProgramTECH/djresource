# DjResource

![Logo DjResource](assets/logo.svg){ align="right" width="140" }

**DjResource** est une bibliothèque pour **Django** qui génère automatiquement les vues CRUD (Create, Read, Update, Delete), le formulaire et les routes d'un modèle — à partir d'une seule classe `Resource`.

Fini le code répétitif : vues, formulaires et templates sont créés pour vous, tout en restant 100 % surchargeables.

## Pourquoi DjResource ?

Dans un projet Django classique, mettre en place le CRUD d'un modèle demande d'écrire à la main :

- 5 vues (List, Create, Read, Update, Delete),
- 1 formulaire (`ModelForm`),
- 4 à 5 templates,
- les routes correspondantes.

C'est répétitif, chronophage, et identique d'un modèle à l'autre. **DjResource remplace tout cela par une classe de quelques lignes :**

```python
class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "prix", "stock"]
    list_display = ["nom", "prix", "stock"]
    search_fields = ["nom"]
    ordering_fields = ["nom", "prix"]
```

Et l'équivalent d'une ligne dans `urls.py` pour brancher les 5 routes.

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| CRUD complet | List, Create, Detail, Update, Delete générés automatiquement |
| Formulaire auto | `ModelForm` créé à partir du modèle et des `fields` |
| Routes nommées | `.urls()` prêt à inclure, noms `<modele>_list`, `<modele>_create`… |
| Recherche | Barre de recherche texte sur les `search_fields` (`?q=`) |
| Tri | Colonnes triables (`?sort=` + `?dir=`) restreintes à `ordering_fields` |
| Pagination | Configurable via `paginate_by` (défaut : 20) |
| Lookup personnalisé | URLs détail/update/delete via n'importe quel champ (`lookup_field` : pk, slug, uid…) |
| 3 thèmes | Bootstrap 5 (défaut), Tailwind, Plain |
| Messages de succès | Via `django.contrib.messages` |
| Optimisation N+1 | `select_related` / `prefetch_related` automatiques |
| Personnalisation | Templates surchargeables, contexte métier, permissions |
| Injection de composants | Balises `{% djresource_list %}` etc. dans n'importe quelle page |

## Démarrage en 30 secondes

```bash
pip install djresource
```

```python
INSTALLED_APPS = [..., "djresource"]
```

```python
# produits/resources.py
from djresource.resource import Resource
from .models import Produit

class ProduitResource(Resource):
    model = Produit
```

```python
# urls.py
from django.urls import include, path
from produits.resources import ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
]
```

!!! success "Résultat"
    `/produits/` (liste), `/produits/nouveau/` (création), `/produits/<pk>/` (détail),
    `/produits/<pk>/modifier/` (modification), `/produits/<pk>/supprimer/` (suppression).

## Documentation

- **Guide** : [Installation](guide/installation.md) → [Démarrage rapide](guide/quickstart.md) → [Thèmes](guide/themes.md) → [Personnalisation](guide/customization.md) → [Fonctionnalités avancées](guide/advanced.md)
- **Référence API** : [Classe Resource](api/resource.md), [Mixins](api/mixins.md), [Balises et filtres](api/templatetags.md)
- [Contribuer](contributing.md) · [Journal des versions](changelog.md)

## Licence

Distribué sous [licence MIT](https://github.com/NockiProgramTECH/djresource/blob/main/LICENSE).
