# Quickstart

This guide shows you how to get a complete CRUD for a Django model in
a few minutes.

## 1. Create your model

```python
# produits/models.py
from django.db import models

class Produit(models.Model):
    nom = models.CharField("Nom", max_length=100)
    prix = models.DecimalField("Prix (FCFA)", max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField("Stock", default=0)
    actif = models.BooleanField("Actif", default=True)
```

Then generate the migrations:

```bash
python manage.py makemigrations produits
python manage.py migrate
```

## 2. Declare a resource

Create a `resources.py` file in your application, and subclass
`Resource`:

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

## 3. Wire up the URLs

```python
# urls.py (racine du projet)
from django.urls import include, path
from produits.resources import ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
]
```

## 4. Test it

Start the server:

```bash
python manage.py runserver
```

Then open **http://127.0.0.1:8000/produits/**.

## What was generated

| URL | View | Route names |
|---|---|---|
| `/produits/` | List (search, sorting, pagination) | `produit_list` |
| `/produits/nouveau/` | Create | `produit_create` |
| `/produits/<pk>/` | Detail | `produit_detail` |
| `/produits/<pk>/modifier/` | Update | `produit_update` |
| `/produits/<pk>/supprimer/` | Delete (confirmation) | `produit_delete` |

!!! tip "Using route names"
    The name is built from the Django model's `model_name`:
    `produit` → `produit_list`, etc. Use `reverse("produit_list")` or
    `{% url "produit_list" %}` in your templates.

Next, let's look at [themes](themes.md).
