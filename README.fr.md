**Français** | [English](README.md)

# djresource

Bibliothèque pour Django qui génère automatiquement les vues CRUD
(Create, Read, Update, Delete), le formulaire et les routes d'un modèle,
à partir d'une seule classe `Resource`.

## Installation

```bash
pip install djresource
```

Puis ajoutez `"djresource"` dans `INSTALLED_APPS` de votre projet Django.
Voir `docs/guide/installation.md` pour les détails.

## 🚀 Démarrage pas à pas dans un TOUT NOUVEAU projet

Cette section est faite pour que tu essaies toi-même, dans un projet vide
(pas le projet `demo/` fourni), avec un exemple différent (une petite
bibliothèque de livres) pour bien comprendre chaque étape.

### Étape 0 — Prérequis

- Python installé (vérifie avec `python --version` dans un terminal).
- Un terminal ouvert (PowerPoint ou CMD sur Windows).

### Étape 1 — Créer le dossier du projet et l'environnement virtuel

```bash
mkdir C:\Users\HP\Desktop\MaBiblio
cd C:\Users\HP\Desktop\MaBiblio

python -m venv .venv
.venv\Scripts\activate
```

Ton invite de commande doit maintenant afficher `(.venv)` au début de la
ligne — ça veut dire que l'environnement virtuel est actif.

```bash
pip install Django
```

### Étape 2 — Créer le projet Django

```bash
django-admin startproject config .
```

Le `.` à la fin est important : ça crée le projet directement dans
`MaBiblio/` au lieu de créer un sous-dossier en plus. Tu dois maintenant
avoir `manage.py` et un dossier `config/` (avec `settings.py`, `urls.py`).

### Étape 3 — Installer djresource dans ton nouveau projet

```bash
pip install djresource
```

> En développement local (depuis ce dépôt) : `pip install -e .`
> à la racine de `DjangoRessource/`, au lieu de copier le dossier à la main.

### Étape 4 — Créer l'app "bibliotheque"

```bash
python manage.py startapp bibliotheque
```

### Étape 5 — Déclarer les apps dans settings.py

Ouvre `config/settings.py`, trouve `INSTALLED_APPS` et ajoute les deux
lignes en gras (conceptuellement) :

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "djresource",       # <- ajouté
    "bibliotheque",     # <- ajouté
]
```

Vérifie aussi que `django.contrib.messages.context_processors.messages`
est bien dans `TEMPLATES` → `OPTIONS` → `context_processors` (c'est le
cas par défaut avec `startproject`, donc normalement rien à faire).

### Étape 6 — Créer le modèle

Ouvre `bibliotheque/models.py` :

```python
from django.conf import settings
from django.db import models


class Livre(models.Model):
    titre = models.CharField("Titre", max_length=200)
    auteur = models.CharField("Auteur", max_length=150)
    annee = models.PositiveIntegerField("Année de publication")
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    disponible = models.BooleanField("Disponible", default=True)

    class Meta:
        verbose_name = "livre"
        verbose_name_plural = "livres"

    def __str__(self):
        return self.titre
```

### Étape 7 — Déclarer la Resource

Crée un fichier `bibliotheque/resources.py` :

```python
from djresource.resource import Resource
from .models import Livre


class LivreResource(Resource):
    model = Livre
    fields = ["titre", "auteur", "annee", "disponible"]
    readonly_fields = ["proprietaire"]
    list_display = ["titre", "auteur", "annee", "disponible"]
    search_fields = ["titre", "auteur"]
    ordering_fields = ["titre", "annee"]

    def scope_queryset(self, queryset, request):
        return queryset.filter(proprietaire=request.user)

    def before_save(self, instance, request, is_new):
        if is_new:
            instance.proprietaire = request.user
```

### Étape 8 — Brancher les routes

Ouvre `config/urls.py` :

```python
from django.contrib import admin
from django.urls import path, include
from bibliotheque.resources import LivreResource

urlpatterns = [
    path("admin/", admin.site.urls),
    path("livres/", include(LivreResource().urls())),
]
```

### Étape 9 — Migrations

```bash
python manage.py makemigrations bibliotheque
python manage.py migrate
```

Si tout se passe bien, tu verras des lignes `Applying bibliotheque.0001_initial... OK`.

### Étape 10 — Lancer et tester

```bash
python manage.py runserver
```

Ouvre `http://127.0.0.1:8000/livres/` dans ton navigateur. Tu es redirigé
vers la connexion tant que tu n'es pas authentifié. Après connexion, crée un
livre et vérifie que la liste ne contient que les livres de l'utilisateur
courant. Le [tutoriel sécurisé complet](docs/fr/guide/quickstart.md) est
également disponible dans la documentation.

**Si ça marche → la bibliothèque est bien intégrée.** Tu peux maintenant
essayer, dans l'ordre, pour t'entraîner :
1. Changer `theme = "tailwind"` sur `LivreResource` et relancer.
2. Ajouter `search_fields` déjà fait — teste `?q=` en tapant dans la
   barre de recherche de la liste.
3. Créer une page perso (`bibliotheque/views.py` + template) qui utilise
   `{% djresource_list_data "bibliotheque.resources.LivreResource" as livres %}`
   pour afficher les livres en cartes plutôt qu'en tableau — voir la
   section "Niveau 3" plus bas, et l'exemple `boutique_*` du projet `demo/`.

### Erreurs fréquentes (et comment les lire)

| Message d'erreur | Cause probable | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'djresource'` | Le dossier `djresource/` n'est pas à la racine, ou l'environnement virtuel n'est pas activé | Vérifie l'emplacement du dossier et que `(.venv)` est affiché dans le terminal |
| `TemplateDoesNotExist: djresource/list.html` | `"djresource"` n'est pas dans `INSTALLED_APPS`, ou mal orthographié | Vérifie l'étape 5 |
| `NoReverseMatch` sur `livre_list` ou similaire | Les routes ne sont pas branchées, ou `LivreResource().urls()` n'est pas inclus | Vérifie l'étape 8 |
| `django.db.utils.OperationalError: no such table` | Migrations pas appliquées | Relance l'étape 9 (`makemigrations` puis `migrate`) |
| Page blanche / erreur 500 avec `DEBUG = True` | Django affiche la trace complète : lis la dernière ligne, elle indique presque toujours le fichier et la ligne fautifs | Copie l'erreur ici si besoin, je t'aide à la lire |

---

## Installation dans un projet existant (résumé rapide)

1. Installer la bibliothèque :
```bash
pip install djresource
```
2. Ajouter `"djresource"` dans `INSTALLED_APPS`.
3. Déclarer une ressource pour votre modèle :

```python
# produits/resources.py
from djresource.resource import Resource
from .models import Produit

class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "prix", "stock"]     # toujours lister explicitement les champs (voir Sécurité)
    list_display = ["nom", "prix", "stock"]
    search_fields = ["nom"]
    ordering_fields = ["nom", "prix"]
```

4. Brancher les routes :

```python
# urls.py
from django.urls import path, include
from produits.resources import ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
]
```

Cela génère automatiquement :

| URL | Vue |
|---|---|
| `/produits/` | Liste (recherche, tri, pagination) |
| `/produits/nouveau/` | Création |
| `/produits/<pk>/` | Détail |
| `/produits/<pk>/modifier/` | Modification |
| `/produits/<pk>/supprimer/` | Suppression (avec confirmation) |

## Trois niveaux de contrôle sur l'affichage

> **Pour un vrai projet (site avec sa propre identité visuelle, e-commerce,
> etc.), le Niveau 3 ci-dessous est le pattern à utiliser.** Les niveaux 1
> et 2 servent surtout à prototyper vite ou à dépanner un dashboard interne
> sans se soucier du design. Dès que vous avez vos propres templates,
> passez directement au Niveau 3 : djresource ne vous impose alors plus
> aucun HTML, seulement la logique (recherche, tri, pagination, validation,
> sauvegarde, redirection).

Du plus rapide (prototypage) au plus libre (site avec identité visuelle propre) :

### Niveau 1 — Templates du framework tels quels

```python
class ProduitResource(Resource):
    model = Produit
    theme = "tailwind"   # "bootstrap" (défaut) | "tailwind" | "plain"
```

- **`"bootstrap"`** (défaut) : Bootstrap 5 via CDN.
- **`"tailwind"`** : Tailwind via CDN (prototype ; prévoir un vrai pipeline de build pour la prod).
- **`"plain"`** : HTML sémantique + CSS minimal (`djresource/static/djresource/css/djresource.css`),
  classes préfixées `djr-`, pensé pour être réécrit à la main.

### Niveau 2 — Composants tout faits injectés dans vos pages

Vous avez déjà une page (dashboard, etc.) et voulez y injecter le tableau
ou le formulaire du thème choisi, tel quel :

```html
{% load djresource_tags %}
<h1>Mon tableau de bord</h1>
{% djresource_list "produits.resources.ProduitResource" %}
{% djresource_form "produits.resources.ProduitResource" %}
{% djresource_detail "produits.resources.ProduitResource" produit.pk %}
```

### Niveau 3 — Données brutes, affichage 100% libre (cartes, e-commerce...)

Aucun HTML n'est imposé : vous bouclez vous-même sur les objets pour
construire cartes, grille, carrousel, avec **n'importe quel framework
CSS** (ou aucun), vos propres classes, vos propres attributs `data-*`, et
vos propres balises `<meta>` (SEO).

```html
{% load djresource_tags %}
{% djresource_list_data "produits.resources.ProduitResource" as produits %}

<div class="ma-grille-de-cartes">
  {% for produit in produits.object_list %}
    <article class="ma-carte" data-produit-id="{{ produit.pk }}">
      <h3>{{ produit.nom }}</h3>
      <p>{{ produit.prix }} FCFA</p>
      <a href="{% url produits.url_detail produit.pk %}">Voir</a>
    </article>
  {% endfor %}
</div>

{% if produits.is_paginated %}
  {% if produits.page_obj.has_next %}
    <a href="?page={{ produits.page_obj.next_page_number }}">Suivant</a>
  {% endif %}
{% endif %}
```

Pour un détail avec ses propres meta tags SEO et du contenu statique :

```html
{% djresource_detail_data "produits.resources.ProduitResource" produit_id as d %}
<title>{{ d.object.nom }}</title>
<meta name="description" content="{{ d.object.description|truncatewords:20 }}">
<h1>{{ d.object.nom }}</h1>
<p>Garantie satisfaction 7 jours — offre valable en boutique.</p>
```

Et pour un formulaire mis en page entièrement à la main — **le pattern le
plus important pour un vrai site** : UN SEUL template, réutilisé pour
créer ET modifier un objet. Cette vue gère les deux cas :

```python
# produits/views.py
from django.shortcuts import render
from .resources import ProduitResource

def produit_formulaire(request, lookup=None):
    """
    lookup=None    -> formulaire de création, vide
    lookup="xyz"   -> formulaire de modification, pré-rempli

    Dans les deux cas, djresource calcule déjà `form` (le ModelForm,
    bindé ou non selon le cas) et `form_action_url` (l'URL de création
    OU de modification, selon le cas) — le template n'a RIEN à savoir
    de cette différence, il poste juste vers `form_action_url`.
    """
    resource = ProduitResource()
    context = resource.get_form_context(request, lookup=lookup)
    return render(request, "produits/mon_formulaire.html", context)
```

```python
# urls.py
path("produits/ajouter/", produit_formulaire, name="produit_ajouter"),
path("produits/<slug:lookup>/modifier/", produit_formulaire, name="produit_modifier"),
```

```html
{# produits/templates/produits/mon_formulaire.html — UN SEUL fichier pour les deux cas #}
<form method="post" action="{{ form_action_url }}" enctype="multipart/form-data">
  {% csrf_token %}
  {% if form.non_field_errors %}<div class="erreur">{{ form.non_field_errors }}</div>{% endif %}
  {% for field in form %}
    <div class="champ">
      <label>{{ field.label }}</label>
      {{ field }}
      {% for error in field.errors %}<div class="erreur">{{ error }}</div>{% endfor %}
    </div>
  {% endfor %}
  <button type="submit">Enregistrer</button>
</form>
```

Django pré-remplit automatiquement le formulaire quand une instance existe
(`ModelForm(instance=...)`, fait par `get_form_context`) : vous n'avez
rien à tester ("si c'est une modification, afficher X") dans le template,
le même code fonctionne dans les deux cas. `enctype="multipart/form-data"`
est obligatoire dès qu'un champ fichier/image existe sur le modèle —
contrairement aux balises `{% djresource_form %}`/`form_partial.html` du
framework (qui l'incluent déjà), un template 100% à vous doit le
déclarer lui-même.

**Exemple complet fonctionnel**, avec liste en cartes ET ce pattern
créer/modifier réutilisé, dans le projet `demo/` : `app/views.py`
(`produits_cartes`, `produit_formulaire`) + `app/templates/app/produits_cartes.html`
+ `app/templates/app/produit_form.html`. Routes : `/cartes/`,
`/cartes/ajouter/`, `/cartes/<slug>/modifier/`.

Les mêmes données sont accessibles depuis une **vue Python**, sans balise
de template, via `get_list_context(request)`, `get_form_context(request, lookup=None)`,
`get_detail_context(request, lookup)` sur `Resource` — utile si vous préférez
tout construire côté vue plutôt que côté template. `lookup` est la valeur
du `lookup_field` de la ressource (`pk` par défaut — voir section dédiée
plus bas).

**Exemple complet fonctionnel** dans le projet de démo : `demo/produits/views.py`
(`boutique_liste`, `boutique_detail`) + `demo/produits/templates/produits/boutique_*.html`
— une page boutique en cartes avec CSS maison (ni Bootstrap, ni Tailwind,
ni le thème du framework), et une fiche produit avec meta tags SEO et
info statique complémentaire (garantie). Routes : `/boutique/` et `/boutique/<pk>/`.

## Identifier les objets autrement que par `pk` (lookup_field)

Par défaut, les URLs de détail/modification/suppression utilisent la clé
primaire (`/produits/3/`). Pour utiliser un autre champ — un slug, un nom,
une référence — sur les URLs :

```python
class ProduitResource(Resource):
    model = Produit
    lookup_field = "slug"   # doit être unique=True sur le modèle
```

Cela génère `/produits/<slug>/`, `/produits/<slug>/modifier/`, etc. Le
framework en déduit automatiquement :
- `lookup_url_kwarg` (nom du paramètre dans l'URL, = `lookup_field` par défaut),
- `lookup_converter` (déduit du type du champ : `int` pour `pk`,
  `slug` pour un `SlugField`, `uuid` pour un `UUIDField`, `str` sinon —
  donc `<slug:slug>` ici). Vous pouvez les surcharger explicitement si besoin.

**Important : `lookup_field` doit être unique en base** (`unique=True` sur
le champ du modèle, ou une clé primaire). Sinon, deux enregistrements
pourraient partager la même URL — le framework émet un `UserWarning` au
démarrage si ce n'est pas le cas (ex: `name = models.CharField(...)` sans
`unique=True` — c'est probablement ce qu'il vous manque si vous avez
défini `lookup_field = "name"`) :

```python
class Produit(models.Model):
    name = models.CharField(max_length=100, unique=True)   # <- ajouter unique=True
```

Sans `unique=True`, la recherche d'un objet par ce champ peut lever une
erreur serveur si deux produits ont le même nom. Un `SlugField` dédié
(`models.SlugField(unique=True)`, généré depuis le nom via `slugify`) est
souvent un meilleur choix qu'un champ texte libre pour un `lookup_field`,
car il est prévu pour être utilisé dans une URL (pas d'espaces, d'accents,
de caractères spéciaux).

Toutes les balises (`djresource_list`, `djresource_detail`, etc.) et les
templates fournis s'adaptent automatiquement au `lookup_field` choisi —
rien d'autre à changer.

## Relations (ForeignKey, OneToOneField, ManyToManyField)

Django gère les relations **nativement** dans le formulaire généré, sans
rien à configurer de plus : il suffit de lister le champ dans `fields`.

```python
class Produit(models.Model):
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE)   # un-à-plusieurs
    fournisseur = models.OneToOneField(Fournisseur, on_delete=models.CASCADE)  # un-à-un
    tags = models.ManyToManyField(Tag, blank=True)                       # plusieurs-à-plusieurs

class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "categorie", "fournisseur", "tags"]
    list_display = ["nom", "categorie", "tags"]
```

- **ForeignKey / OneToOneField** : devient une liste déroulante (`<select>`)
  proposant les objets liés, affichés via leur `__str__` — comportement
  Django standard.
- **ManyToManyField** : devient une liste à sélection multiple. Pour un
  widget plus agréable (cases à cocher, champ à tags...), passez par le
  Niveau 3 (`{% djresource_form_data %}`) et construisez le rendu du champ
  vous-même — le champ Django (`form.tags`) reste disponible tel quel.
- **Affichage en liste/détail** : `list_display` et la fiche détail
  affichent automatiquement une FK via son `__str__`, et un M2M (ou une
  relation inversée) sous forme de liste lisible séparée par des virgules
  (ex: `Électronique, Promo`).
- **Performance** : ajoutez les FK à `select_related` et les M2M /
  relations inversées à `prefetch_related` pour éviter les requêtes N+1
  quand elles apparaissent dans `list_display` :

```python
class ProduitResource(Resource):
    model = Produit
    list_display = ["nom", "categorie", "tags"]
    select_related = ["categorie", "fournisseur"]
    prefetch_related = ["tags"]
```

## Champs fichier / image (FileField, ImageField)

Pour un `ImageField`, installez Pillow (`pip install Pillow`) et
configurez `MEDIA_URL`/`MEDIA_ROOT` dans `settings.py` :

```python
# settings.py
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
```

```python
# urls.py, uniquement pour le développement (DEBUG=True)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [...]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Piège fréquent (déjà corrigé dans le framework) :** un formulaire HTML
qui contient un champ fichier doit avoir `enctype="multipart/form-data"`
sur la balise `<form>`, sinon le navigateur n'envoie jamais le fichier —
Django reçoit `request.FILES` vide et affiche "This field is required."
même si un fichier a bien été sélectionné (souvent sans autre erreur
visible : la requête répond 200, c'est juste le formulaire invalide qui se
réaffiche). Tous les templates de formulaire du framework (`form.html`,
`form_partial.html`, dans les 3 thèmes) l'ont désormais.

## Personnaliser le formulaire généré (n'importe quel framework CSS)

Indépendamment du thème, contrôle total champ par champ :

```python
class ProduitResource(Resource):
    model = Produit
    widget_classes = {
        "nom": "input input-bordered w-full",   # ex : classes DaisyUI
        "prix": "input input-bordered w-full",
    }
    widget_attrs = {
        "nom": {"data-testid": "champ-nom", "maxlength": "100"},
    }
```

`widget_classes` prend le pas sur `auto_form_css`/`theme` pour les champs
listés (les autres gardent le style du thème). `widget_attrs` ajoute
n'importe quel attribut HTML (data-*, aria-*, maxlength...) sans toucher
aux classes CSS. Pour désactiver complètement l'injection automatique :

```python
class ProduitResource(Resource):
    model = Produit
    auto_form_css = False
```

## Ajouter des informations métier dans les pages du framework

Pour l'autre sens — ajouter une info dans une page générée par djresource
plutôt que le contraire :

**`get_extra_context()`** : injecté automatiquement dans toutes les vues générées.

```python
class ProduitResource(Resource):
    model = Produit
    def get_extra_context(self, view):
        return {"valeur_stock_total": ...}
```

**Blocks de template** : `list_top`, `list_bottom`, `list_header_actions`,
`form_top`, `form_bottom`, `detail_extra`, disponibles dans les pages
complètes de chaque thème.

```html
{% extends "djresource/list.html" %}
{% block list_top %}
<div class="alert alert-info">Stock total : {{ valeur_stock_total }} FCFA</div>
{% endblock %}
```

## ⚠️ Sécurité — à lire avant tout déploiement

1. **Authentification obligatoire par défaut.** Les vues CRUD et les
   composants injectés exigent un utilisateur connecté. Pour rendre une
   ressource publique, activez-le explicitement avec `public = True` :

   ```python
   class ProduitResource(Resource):
       model = Produit
       public = True
   ```

2. **Isoler tous les accès aux objets.** Surchargez
   `scope_queryset(queryset, request)` pour isoler les propriétaires/tenants.
   Le `get_queryset(request)` obtenu est utilisé pour la liste, le détail,
   la modification, la suppression et les contextes injectés :

   ```python
   class ArticleScopedResource(Resource):
       model = Article
       fields = ["titre", "slug"]

       def scope_queryset(self, queryset, request=None):
           if request is None or not request.user.is_authenticated:
               return queryset.none()
           return queryset.filter(owner=request.user)

       def before_save(self, instance, request, is_new):
           if is_new:
               instance.owner = request.user
   ```

   Par défaut, `get_permissions()` retourne `[LoginRequiredMixin]` (ou `[]`
   avec `public = True`). Une surcharge remplace cette politique : conservez
   l’authentification dans vos mixins personnalisés. L’accès public inclut les
   écritures. La connexion seule ne garantit ni les permissions modèle ni
   l’isolation par propriétaire. Le scope ne filtre pas les choix FK/M2M des
   formulaires : adaptez `get_form_class()` pour limiter les objets autorisés.

3. **Aucun champ modifiable par défaut.** `fields = []` est la valeur par défaut.
   Listez explicitement les champs autorisés en écriture. La valeur historique
   `fields = "__all__"` reste supportée avec un `FieldsAllWarning` pour
   compatibilité, mais ne doit pas être utilisée avec des champs sensibles.

4. **Les balises `djresource_*` importent dynamiquement** (`import_string`)
   le chemin passé en argument. Ce chemin doit **toujours** être une
   chaîne codée en dur dans le template, jamais construite depuis une
   donnée utilisateur. Le framework vérifie que la classe résolue hérite
   bien de `Resource`, mais cela ne protège pas contre un chemin
   dynamique malveillant.

5. **Déjà couvert, pour info :**
   - Recherche (`?q=`) : passe par l'ORM (`Q(...)`), paramétrée.
   - Tri (`?sort=`) : vérifié contre une liste blanche (`ordering_fields`).
   - `readonly_fields` : Django ignore la valeur POST soumise pour un
     champ désactivé.
   - `pk` inexistant : renvoie une 404 propre (`get_object_or_404`).
   - CSRF : `{% csrf_token %}` présent dans tous les formulaires, y
     compris les templates partiels.

6. **Projet de démo (`demo/`) : ne pas utiliser tel quel en production**
   (`SECRET_KEY` codée en dur, `DEBUG = True`, `ALLOWED_HOSTS = ["*"]`).

## Options de configuration disponibles

| Attribut | Rôle |
|---|---|
| `model` | Modèle Django (obligatoire) |
| `fields` | Liste blanche des champs du formulaire (vide par défaut) |
| `readonly_fields` | Champs affichés mais non modifiables |
| `list_display` | Colonnes affichées dans la liste |
| `search_fields` | Champs concernés par la recherche texte |
| `ordering_fields` | Champs sur lesquels le tri par clic est autorisé |
| `list_filter` | Champs filtrables via `?champ=valeur` (booléens, champs à `choices`) |
| `paginate_by` | Nombre d'objets par page (défaut : 20) |
| `select_related` / `prefetch_related` | Optimisation des requêtes sur les relations |
| `lookup_field` | Champ utilisé pour identifier l'objet dans les URLs (`"pk"` par défaut — voir section dédiée) |
| `theme` | `"bootstrap"` (défaut) \| `"tailwind"` \| `"plain"` \| thème custom |
| `auto_form_css` | Injection auto des classes CSS du thème sur le formulaire |
| `widget_classes` / `widget_attrs` | Classes CSS et attributs HTML par champ, indépendants du thème |
| `template_list/detail/form/delete` | Surcharge d'un template précis |
| `get_extra_context(view)` | Injecte des données métier dans le contexte de toutes les vues |
| `get_list_context/get_form_context/get_detail_context` | Contexte calculé hors vue (affichage 100% custom) |
| `inlines` | Définitions inline ; liste vide par défaut |
| `clean(instance, request)` | Valider avant sauvegarde ; lever ValidationError |
| `before_save(instance, request, is_new)` | Modifier avant sauvegarde |
| `after_save(instance, request, is_new)` | Réagir après parent/M2M, avant les inlines |
| `before_delete(instance, request)` | Bloquer la suppression avec ValidationError |
| `after_delete(instance, request)` | Réagir après suppression |
| `public` | Active explicitement l'accès sans authentification |
| `get_permissions()` | Mixins de permission supplémentaires (authentification par défaut) |
| `scope_queryset(queryset, request)` / `get_queryset(request)` | Isolation des objets selon la requête |

## Balises de template disponibles (`{% load djresource_tags %}`)

| Balise | Rend du HTML ? | Usage |
|---|---|---|
| `djresource_list "chemin.Resource"` | Oui (thème choisi) | Injecter le composant liste tout fait |
| `djresource_form "chemin.Resource" [lookup]` | Oui | Injecter le composant formulaire tout fait |
| `djresource_detail "chemin.Resource" lookup` | Oui | Injecter le composant détail tout fait |
| `djresource_list_data "chemin.Resource" as v` | Non | Données brutes de la liste, affichage 100% libre |
| `djresource_form_data "chemin.Resource" [lookup] as v` | Non | Données brutes du formulaire |
| `djresource_detail_data "chemin.Resource" lookup as v` | Non | Données brutes du détail |

`lookup` est la valeur du `lookup_field` de la ressource — `produit.pk`
dans le cas par défaut, ou par ex. `produit.slug` si `lookup_field = "slug"`.

## Lancer le projet de démonstration (celui déjà fourni, produits/boutique)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

cd demo
python manage.py makemigrations produits
python manage.py migrate
python manage.py runserver
```

- `http://127.0.0.1:8000/produits/` — CRUD généré (thème par défaut).
- `http://127.0.0.1:8000/dashboard/` — page custom avec le composant tout fait injecté.
- `http://127.0.0.1:8000/boutique/` — page e-commerce en cartes, données brutes, CSS maison.
- `http://127.0.0.1:8000/boutique/<pk>/` — fiche produit avec meta tags SEO + info statique.

## Lancer les tests

```bash
python runtests.py
```

## Hooks métier et formsets inline

Surchargez `clean(instance, request)` pour lever une `ValidationError` Django et
réafficher le formulaire. `before_save(instance, request, is_new)` peut assigner
le propriétaire ; `after_save(instance, request, is_new)` suit la sauvegarde du
parent et des M2M. `before_delete(instance, request)` peut lever `ValidationError`
pour bloquer la suppression ; `after_delete(instance, request)` ne s'exécute
qu'après suppression (le pk est alors effacé). Par défaut, ces hooks ne font rien.
Les inlines sont sauvegardés après `after_save`, dans la même transaction.
Utilisez `transaction.on_commit()` pour les effets externes.

```python
from django.forms import inlineformset_factory

class NoteInline:
    def get_formset_class(self, parent_model):
        return inlineformset_factory(parent_model, Note, fields=["text"], extra=1)

class ArticleWithNotesResource(Resource):
    model = Article
    fields = ["titre", "slug"]
    inlines = [NoteInline()]  # Note possède une ForeignKey vers Article
```

Les formsets sont validés avant toute écriture et sauvegardés après attribution
du pk parent. Chaque inline doit avoir un préfixe de formset distinct. Les thèmes
fournis affichent les champs de gestion et les erreurs. Les formulaires
personnalisés doivent afficher `inline_formsets`.

## Signaux Django

```python
from django.dispatch import receiver
from djresource.signals import resource_post_save

@receiver(resource_post_save, sender=Article)
def article_saved(sender, instance, resource, **kwargs):
    pass  # réagir sans hériter de Resource
```

`resource_pre_save` suit `before_save` ; `resource_post_save` suit `after_save`
(parent/M2M sauvegardés, pas encore les inlines) ; `resource_post_delete` suit
`after_delete` (pk effacé). Tous transmettent `instance` et `resource`, avec
`sender=resource.model`. Un refus de validation n’émet rien. Les récepteurs sont
synchrones, leurs exceptions se propagent ; utilisez `transaction.on_commit()`
pour les effets externes. Les écritures ORM directes et opérations groupées
n’émettent pas ces signaux.

## HTMX (optionnel)

Activez `htmx = True` sur la Resource. Les requêtes avec `HX-Request: true`
affichent `list_partial`, `form_partial`, `detail_partial` ou
`confirm_delete_partial` au lieu de la page complète (trois thèmes). Un formulaire
invalide renvoie aussi un partiel ; une écriture réussie conserve sa redirection.
Les autres requêtes restent inchangées. Permissions et CSRF restent appliqués,
et les réponses varient selon `HX-Request`. Chargez HTMX vous-même ; par exemple,
un bouton peut utiliser `hx-get="/articles/"` et `hx-target="#articles"`.
La sélection des partiels suit le thème, pas les surcharges de page complète.
Surchargez `get_template_names()` de la vue générée pour un partiel personnalisé.
