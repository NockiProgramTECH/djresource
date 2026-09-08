# Démarrage rapide

Ce guide vous montre comment obtenir un CRUD complet pour un modèle Django en
quelques minutes.

## 1. Créer votre modèle

```python
# produits/models.py
from django.db import models

class Produit(models.Model):
    nom = models.CharField("Nom", max_length=100)
    prix = models.DecimalField("Prix (FCFA)", max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField("Stock", default=0)
    actif = models.BooleanField("Actif", default=True)
```

Puis générez les migrations :

```bash
python manage.py makemigrations produits
python manage.py migrate
```

## 2. Déclarer une ressource

Créez un fichier `resources.py` dans votre application, et héritez de
`Resource` :

```python
# produits/resources.py
from djresource.resource import Resource
from .models import Produit

class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "prix", "stock", "actif"]
    list_display = ["nom", "prix", "stock", "actif"]
    search_fields = ["nom"]
    ordering_fields = ["nom", "prix", "stock"]
```

## 3. Brancher les routes

```python
# urls.py (racine du projet)
from django.urls import include, path
from produits.resources import ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
]
```

## 4. Tester

Lancez le serveur :

```bash
python manage.py runserver
```

Puis ouvrez **http://127.0.0.1:8000/produits/**.

## Ce qui a été généré

| URL | Vue | Noms des routes |
|---|---|---|
| `/produits/` | Liste (recherche, tri, pagination) | `produit_list` |
| `/produits/nouveau/` | Création | `produit_create` |
| `/produits/<pk>/` | Détail | `produit_detail` |
| `/produits/<pk>/modifier/` | Modification | `produit_update` |
| `/produits/<pk>/supprimer/` | Suppression (confirmation) | `produit_delete` |

!!! tip "Utiliser les noms de routes"
    Le nom est construit à partir du `model_name` du modèle Django :
    `produit` → `produit_list`, etc. Utilisez `reverse("produit_list")` ou
    `{% url "produit_list" %}` dans vos templates.

Passons maintenant aux [thèmes](themes.md).
