<p align="center">
  <img src="https://raw.githubusercontent.com/NockiProgramTECH/djresource/main/docs/assets/logo.svg" alt="DjResource" width="120" />
</p>

<h1 align="center">DjResource</h1>

<p align="center">
  <em>Générez tout le CRUD Django d'un modèle en une seule classe.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/djresource/"><img src="https://img.shields.io/pypi/v/djresource.svg?color=4f46e5&label=PyPI" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/djresource/"><img src="https://img.shields.io/pypi/pyversions/djresource.svg?color=4f46e5" alt="Versions Python" /></a>
  <a href="https://pypi.org/project/djresource/"><img src="https://img.shields.io/pypi/djversions/djresource.svg?color=4f46e5" alt="Versions Django" /></a>
  <a href="https://github.com/NockiProgramTECH/djresource/actions/workflows/test.yml"><img src="https://github.com/NockiProgramTECH/djresource/actions/workflows/test.yml/badge.svg" alt="Tests" /></a>
  <a href="https://github.com/NockiProgramTECH/djresource/actions/workflows/docs.yml"><img src="https://github.com/NockiProgramTECH/djresource/actions/workflows/docs.yml/badge.svg" alt="Documentation" /></a>
  <a href="https://github.com/NockiProgramTECH/djresource/blob/main/LICENSE"><img src="https://img.shields.io/badge/licence-MIT-4f46e5.svg" alt="Licence MIT" /></a>
</p>

---

**DjResource** est une bibliothèque pour **Django** qui génère automatiquement les vues CRUD (Create, Read, Update, Delete), le formulaire et les routes d'un modèle — à partir d'une seule classe `Resource`. Fini le code répétitif : vues, formulaires et templates sont créés pour vous, tout en restant 100 % surchargeables.

- **⚡ Zéro code CRUD à écrire** : une classe, cinq routes, un CRUD complet.
- **🎨 3 thèmes prêts à l'emploi** : Bootstrap 5, Tailwind, Plain.
- **🔌 Extensible** : templates surchargeables, contexte métier, permissions.
- **🛡️ Sécurisé** : permissions appliquées aux partiels injectés, garde-fou anti-mass assignment.
- **📦 Prêt pour la production** : recherche, tri, pagination, messages de succès, optimisation N+1.

---

## 🚀 Installation

```bash
pip install djresource
```

Puis ajoutez `"djresource"` dans `INSTALLED_APPS` :

```python
INSTALLED_APPS = [
    # ...
    "djresource",
]
```

## ⚡ Démarrage rapide

Déclarez une ressource pour votre modèle :

```python
# produits/resources.py
from djresource.resource import Resource
from .models import Produit

class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "prix", "stock"]
    list_display = ["nom", "prix", "stock"]
    search_fields = ["nom"]
    ordering_fields = ["nom", "prix"]
```

Branchez les routes — **une seule ligne** :

```python
# urls.py
from django.urls import path, include
from produits.resources import ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
]
```

C'est tout. Le CRUD complet est disponible :

| URL | Vue |
|---|---|
| `/produits/` | Liste (recherche, tri, pagination) |
| `/produits/nouveau/` | Création |
| `/produits/<pk>/` | Détail |
| `/produits/<pk>/modifier/` | Modification |
| `/produits/<pk>/supprimer/` | Suppression (avec confirmation) |

## 🎨 Thèmes

Choisissez le style visuel avec l'attribut `theme` :

```python
class ProduitResource(Resource):
    model = Produit
    theme = "tailwind"   # "bootstrap" (défaut) | "tailwind" | "plain"
```

- **`"bootstrap"`** (défaut) — Bootstrap 5 via CDN.
- **`"tailwind"`** — Tailwind via CDN (`cdn.tailwindcss.com`, idéal pour prototyper).
- **`"plain"`** — HTML sémantique + feuille de style minimale (classes `djr-`), parfait pour écrire son propre CSS.

## 🔗 Changer le champ de lookup dans les URLs

Par défaut les URLs de détail, modification et suppression utilisent le pk du
modèle (`<int:pk>`). Vous pouvez les basculer sur n'importe quel champ du
modèle via l'attribut `lookup_field` :

```python
class ProduitResource(Resource):
    model = Produit
    lookup_field = "slug"        # → <slug:slug> dans les URLs
    # ou "uid" / "uuid" / "code" / tout champ du modèle
```

Les URLs générées deviennent :
`/produits/riz-local/`, `/produits/riz-local/modifier/`, etc.

La bibliothèque détecte automatiquement le type du champ et choisit le
convertisseur Django approprié :

| Champ | Convertisseur | Exemple d'URL |
|---|---|---|
| `IntegerField` / `AutoField` (pk) | `<int:nom>` | `/produits/42/` |
| `SlugField` | `<slug:nom>` | `/produits/riz-local/` |
| `UUIDField` | `<uuid:nom>` | `/produits/550e8400-.../` |
| tout autre champ (`CharField`…) | `<str:nom>` | `/produits/CODE123/` |

Les templates s'adaptent automatiquement : les liens `Voir`, `Modifier`,
`Supprimer` dans les listes et les détails utilisent la valeur du champ de
lookup. Exemple complet avec `lookup_field = "slug"` : modèle `Article` et
resource `ArticleResource` dans la suite de tests (`tests/models.py`,
`tests/resources.py`, `tests/test_crud.py`).

## 🛡️ Sécurité

- **Permissions protégées partout** : les permissions déclarées dans
  `get_permissions()` (ex. `LoginRequiredMixin`) protègent les pages pleine
  page **ET** les composants injectés par les balises `djresource_*`. Un
  visiteur anonyme ne peut pas lire les données d'une Resource protégée via
  une page publique.
- **Anti-mass assignment** : `fields = "__all__"` (défaut) expose tous les
  champs du modèle dans le formulaire. La bibliothèque émet un
  `FieldsAllWarning` à l'instanciation pour vous pousser à déclarer
  explicitement les champs modifiables :
  ```python
  class ProduitResource(Resource):
      model = Produit
      fields = ["nom", "prix", "stock"]   # uniquement ces champs
  ```

## 🧩 Injecter le CRUD dans VOS propres pages

Vous avez déjà codé votre site (navbar, CSS, mise en page) ? Plutôt que
d'hériter des pages pleine page de la bibliothèque, injectez **uniquement le
composant** (tableau, formulaire, détail) au milieu de vos templates :

```html
{% load djresource_tags %}

<h1>Mes produits</h1>
{% djresource_list "produits.resources.ProduitResource" %}
```

| Balise | Rend |
|---|---|
| `{% djresource_list "app.resources.MaResource" %}` | Tableau (recherche, tri, pagination) |
| `{% djresource_form "app.resources.MaResource" %}` | Formulaire de création |
| `{% djresource_form "app.resources.MaResource" objet.slug %}` | Formulaire de modification |
| `{% djresource_detail "app.resources.MaResource" objet.slug %}` | Détail d'un objet |

> Le 2ᵉ argument des balises `djresource_form` / `djresource_detail` est la
> valeur du champ `lookup_field` de la Resource : `objet.pk` (par défaut),
> `objet.slug`, `objet.uid`… selon votre configuration.

Le partiel rendu (`*_partial.html`, décliné par thème) ne contient ni
`<html>`, ni navbar : uniquement le composant, avec les classes du thème de
votre `Resource`. Recherche, tri et pagination fonctionnent via les paramètres
GET de votre page (`?q=`, `?sort=`, `?page=`), sans route supplémentaire.

Pour configurer le composant : passez des `cle=valeur` (fusionnées dans le
contexte du partiel) ou surchargez le partiel via `template=...` ou en
étendant son template et en remplissant ses blocks (`list_top`, `list_bottom`,
`form_top`, `form_bottom`, `detail_extra`). Toutes les données de la vue
correspondante sont disponibles dans le partiel : `resource`, `verbose_name`,
les URL nommées (`url_list`, `url_create`, `url_update`, `url_delete`),
`object_list`, `page_obj`, `list_display` et le résultat de
`get_extra_context()`. Voir l'exemple complet
`demo/produits/templates/produits/boutique.html` (page "boutique" 100 %
personnalisée avec tableau + formulaire + fiche produit injectés).

## 📚 Documentation complète

La documentation complète est disponible sur **[nockiprogramtech.github.io/djresource](https://nockiprogramtech.github.io/djresource/)** :

- [Guide d'installation](https://nockiprogramtech.github.io/djresource/guide/installation/)
- [Démarrage rapide](https://nockiprogramtech.github.io/djresource/guide/quickstart/)
- [Thèmes](https://nockiprogramtech.github.io/djresource/guide/themes/)
- [Personnalisation](https://nockiprogramtech.github.io/djresource/guide/customization/)
- [Fonctionnalités avancées](https://nockiprogramtech.github.io/djresource/guide/advanced/)
- [Référence API](https://nockiprogramtech.github.io/djresource/api/resource/)

## 🧪 Lancer les tests

```bash
pip install -e ".[test]"
python runtests.py
```

## 🤝 Contribuer

Les contributions sont les bienvenues ! Consultez le [guide de contribution](https://nockiprogramtech.github.io/djresource/contributing/) et le [journal des modifications](https://nockiprogramtech.github.io/djresource/changelog/).

## 📄 Licence

Distribué sous la [licence MIT](https://github.com/NockiProgramTECH/djresource/blob/main/LICENSE).

---

<p align="center">
  Fait avec ❤️ par <a href="https://github.com/NockiProgramTECH">Enock Lankonadé</a>
</p>
