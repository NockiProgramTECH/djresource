# Tutoriel depuis zéro

Ce tutoriel crée une petite application de bibliothèque sécurisée depuis un
répertoire vide. Il nécessite Python 3.9+ et Django 4.2+.

## 1. Créer le projet

```bash
mkdir ma-bibliotheque
cd ma-bibliotheque
python -m venv .venv
# Windows :
.venv\Scripts\activate
# macOS/Linux :
source .venv/bin/activate
python -m pip install Django djresource
django-admin startproject config .
python manage.py startapp livres
```

Ajoutez les deux applications dans `config/settings.py` :

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "djresource",
    "livres",
]
```

Conservez le middleware d'authentification Django et le context processor de
requête. Les CRUD générés par DjResource sont protégés par défaut.

## 2. Créer le modèle

```python
# livres/models.py
from django.conf import settings
from django.db import models


class Livre(models.Model):
    titre = models.CharField(max_length=200)
    auteur = models.CharField(max_length=150)
    annee_publication = models.PositiveIntegerField()
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="livres",
    )
    archive = models.BooleanField(default=False)

    def __str__(self):
        return self.titre
```

Lancez les migrations :

```bash
python manage.py makemigrations
python manage.py migrate
```

## 3. Déclarer une Resource sécurisée

Créez `livres/resources.py`. `fields` est une **liste blanche d'écriture** :
les champs qui n'y figurent pas ne peuvent pas être modifiés par le formulaire
généré. Le hook `scope_queryset()` empêche un utilisateur d'accéder aux
objets d'un autre utilisateur.

```python
# livres/resources.py
from djresource.resource import Resource
from .models import Livre


class LivreResource(Resource):
    model = Livre
    fields = ["titre", "auteur", "annee_publication"]
    readonly_fields = ["proprietaire", "archive"]
    list_display = ["titre", "auteur", "annee_publication", "archive"]
    search_fields = ["titre", "auteur"]
    ordering_fields = ["titre", "annee_publication"]

    def scope_queryset(self, queryset, request):
        return queryset.filter(proprietaire=request.user)

    def before_save(self, instance, request, is_new):
        if is_new:
            instance.proprietaire = request.user
```

N'utilisez pas `fields = "__all__"` pour les nouvelles ressources. Cette
valeur reste disponible uniquement pour compatibilité et émet
`FieldsAllWarning`.

## 4. Ajouter les URLs

```python
# config/urls.py
from django.contrib import admin
from django.urls import include, path
from livres.resources import LivreResource

urlpatterns = [
    path("admin/", admin.site.urls),
    path("livres/", include(LivreResource().urls())),
]
```

## 5. Créer un utilisateur et tester le CRUD

```bash
python manage.py createsuperuser
python manage.py runserver
```

Ouvrez `http://127.0.0.1:8000/livres/`. Un visiteur anonyme est redirigé
vers la page de connexion. Après connexion, les routes générées sont :

| URL | Utilité |
|---|---|
| `/livres/` | Liste isolée avec recherche, tri et pagination |
| `/livres/nouveau/` | Création d'un livre appartenant à l'utilisateur |
| `/livres/<pk>/` | Détail limité aux livres de l'utilisateur |
| `/livres/<pk>/modifier/` | Modification limitée aux livres de l'utilisateur |
| `/livres/<pk>/supprimer/` | Suppression limitée aux livres de l'utilisateur |

Créez un deuxième utilisateur et vérifiez qu'il ne peut ni voir ni modifier
les livres du premier. Un objet hors périmètre renvoie HTTP 404, y compris
pour le détail, la modification et la suppression.

## 6. Rendre volontairement une ressource publique

L'accès public est opt-in et sans ambiguïté :

```python
class CataloguePublicResource(Resource):
    model = Livre
    public = True
    fields = []
    list_display = ["titre", "auteur"]
```

Utilisez ceci uniquement pour des données réellement publiques. `public = True`
ne désactive ni `scope_queryset()` ni les règles métier supplémentaires que
vous implémentez.

Consultez ensuite les pages [thèmes](themes.md),
[personnalisation](customization.md) et
[fonctionnalités avancées](advanced.md).
