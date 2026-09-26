**English** | [Français](README.fr.md)

# djresource

Library for Django that automatically generates the CRUD views
(Create, Read, Update, Delete), the form and the routes of a model,
from a single `Resource` class.

## Installation

```bash
pip install djresource
```

Then add `"djresource"` to `INSTALLED_APPS` in your Django project.
See `docs/guide/installation.md` for details.

## 🚀 Step-by-step setup in a BRAND NEW project

This section is made for you to try it yourself, in an empty project
(not the provided `demo/` project), with a different example (a small
book library) to fully understand each step.

### Step 0 — Prerequisites

- Python installed (check with `python --version` in a terminal).
- An open terminal (PowerShell or CMD on Windows).

### Step 1 — Create the project folder and the virtual environment

```bash
mkdir C:\Users\HP\Desktop\MaBiblio
cd C:\Users\HP\Desktop\MaBiblio

python -m venv .venv
.venv\Scripts\activate
```

Your command prompt should now display `(.venv)` at the start of the
line — this means the virtual environment is active.

```bash
pip install Django
```

### Step 2 — Create the Django project

```bash
django-admin startproject config .
```

The trailing `.` is important: it creates the project directly inside
`MaBiblio/` instead of creating an extra subfolder. You should now
have `manage.py` and a `config/` folder (with `settings.py`, `urls.py`).

### Step 3 — Install djresource in your new project

```bash
pip install djresource
```

> For local development (from this repository): `pip install -e .`
> at the root of `DjangoRessource/`, instead of copying the folder by hand.

### Step 4 — Create the "bibliotheque" app

```bash
python manage.py startapp bibliotheque
```

### Step 5 — Declare the apps in settings.py

Open `config/settings.py`, find `INSTALLED_APPS` and add the two
bold (conceptually) lines:

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

Also check that `django.contrib.messages.context_processors.messages`
is present in `TEMPLATES` → `OPTIONS` → `context_processors` (this is
the default with `startproject`, so normally there is nothing to do).

### Step 6 — Create the model

Open `bibliotheque/models.py`:

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

### Step 7 — Declare the Resource

Create a `bibliotheque/resources.py` file:

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

### Step 8 — Wire up the routes

Open `config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from bibliotheque.resources import LivreResource

urlpatterns = [
    path("admin/", admin.site.urls),
    path("livres/", include(LivreResource().urls())),
]
```

### Step 9 — Migrations

```bash
python manage.py makemigrations bibliotheque
python manage.py migrate
```

If everything goes well, you will see lines such as `Applying bibliotheque.0001_initial... OK`.

### Step 10 — Run and test

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/livres/` in your browser. You are redirected
to login until you authenticate. After login, create a book and verify that
the list only contains books owned by the current user. The complete
security-first tutorial is also available in
[the documentation](docs/en/guide/quickstart.md).

**If it works → the library is correctly integrated.** You can now
try, in order, to practice:
1. Set `theme = "tailwind"` on `LivreResource` and restart.
2. `search_fields` is already done — test `?q=` by typing in the
   list search bar.
3. Create a custom page (`bibliotheque/views.py` + template) that uses
   `{% djresource_list_data "bibliotheque.resources.LivreResource" as livres %}`
   to display books as cards rather than as a table — see the
   "Level 3" section below, and the `boutique_*` example of the `demo/` project.

### Common errors (and how to read them)

| Error message | Likely cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'djresource'` | The `djresource/` folder is not at the root, or the virtual environment is not activated | Check the folder location and that `(.venv)` is displayed in the terminal |
| `TemplateDoesNotExist: djresource/list.html` | `"djresource"` is not in `INSTALLED_APPS`, or is misspelled | Check step 5 |
| `NoReverseMatch` on `livre_list` or similar | The routes are not wired up, or `LivreResource().urls()` is not included | Check step 8 |
| `django.db.utils.OperationalError: no such table` | Migrations not applied | Repeat step 9 (`makemigrations` then `migrate`) |
| Blank page / 500 error with `DEBUG = True` | Django displays the full traceback: read the last line, it almost always indicates the faulty file and line | Copy the error if you need help reading it |

---

## Installing in an existing project (quick summary)

1. Install the library:
```bash
pip install djresource
```
2. Add `"djresource"` to `INSTALLED_APPS`.
3. Declare a resource for your model:

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

4. Wire up the routes:

```python
# urls.py
from django.urls import path, include
from produits.resources import ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
]
```

This automatically generates:

| URL | View |
|---|---|
| `/produits/` | List (search, sorting, pagination) |
| `/produits/nouveau/` | Creation |
| `/produits/<pk>/` | Detail |
| `/produits/<pk>/modifier/` | Update |
| `/produits/<pk>/supprimer/` | Deletion (with confirmation) |

## Three levels of control over the display

> **For a real project (site with its own visual identity, e-commerce,**
> **etc.), Level 3 below is the pattern to use.** Levels 1
> and 2 are mostly useful to prototype quickly or to troubleshoot an internal dashboard
> without worrying about design. As soon as you have your own templates,
> go straight to Level 3: djresource then imposes no
> HTML on you, only logic (search, sorting, pagination, validation,
> saving, redirection).

From fastest (prototyping) to most flexible (site with its own visual identity):

### Level 1 — Library templates as is

```python
class ProduitResource(Resource):
    model = Produit
    theme = "tailwind"   # "bootstrap" (défaut) | "tailwind" | "plain"
```

- **`"bootstrap"`** (default): Bootstrap 5 via CDN.
- **`"tailwind"`**: Tailwind via CDN (prototype; plan a real build pipeline for production).
- **`"plain"`**: semantic HTML + minimal CSS (`djresource/static/djresource/css/djresource.css`),
  `djr-`-prefixed classes, designed to be rewritten by hand.

### Level 2 — Ready-made components injected into your pages

You already have a page (dashboard, etc.) and want to inject the table
or the form of the chosen theme into it, as is:

```html
{% load djresource_tags %}
<h1>Mon tableau de bord</h1>
{% djresource_list "produits.resources.ProduitResource" %}
{% djresource_form "produits.resources.ProduitResource" %}
{% djresource_detail "produits.resources.ProduitResource" produit.pk %}
```

### Level 3 — Raw data, 100% free display (cards, e-commerce...)

No HTML is imposed: you loop over the objects yourself to
build cards, grids, carousels, with **any CSS framework**
(or none), your own classes, your own `data-*` attributes, and
your own `<meta>` tags (SEO).

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

For a detail view with its own SEO meta tags and static content:

```html
{% djresource_detail_data "produits.resources.ProduitResource" produit_id as d %}
<title>{{ d.object.nom }}</title>
<meta name="description" content="{{ d.object.description|truncatewords:20 }}">
<h1>{{ d.object.nom }}</h1>
<p>Garantie satisfaction 7 jours — offre valable en boutique.</p>
```

And for a fully hand-laid-out form — **the most important pattern
for a real site**: A SINGLE template, reused to
create AND update an object. This view handles both cases:

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

Django automatically pre-fills the form when an instance exists
(`ModelForm(instance=...)`, done by `get_form_context`): you have
nothing to test ("if this is an update, display X") in the template,
the same code works in both cases. `enctype="multipart/form-data"`
is required as soon as a file/image field exists on the model —
unlike the `{% djresource_form %}` tags / `form_partial.html` from
the library (which already include it), a 100% custom template must
declare it itself.

**Full working example**, with a card list AND this reused
create/update pattern, in the `demo/` project: `app/views.py`
(`produits_cartes`, `produit_formulaire`) + `app/templates/app/produits_cartes.html`
+ `app/templates/app/produit_form.html`. Routes: `/cartes/`,
`/cartes/ajouter/`, `/cartes/<slug>/modifier/`.

The same data is available from a **Python view**, without template
tags, via `get_list_context(request)`, `get_form_context(request, lookup=None)`,
`get_detail_context(request, lookup)` on `Resource` — useful if you prefer
to build everything on the view side rather than the template side. `lookup` is the value
of the resource's `lookup_field` (`pk` by default — see the dedicated
section below).

**Full working example** in the demo project: `demo/produits/views.py`
(`boutique_liste`, `boutique_detail`) + `demo/produits/templates/produits/boutique_*.html`
— a card-based shop page with custom CSS (neither Bootstrap, nor Tailwind,
nor the library theme), and a product page with SEO meta tags and
additional static info (warranty). Routes: `/boutique/` and `/boutique/<pk>/`.

## Identifying objects by something other than `pk` (lookup_field)

By default, detail/update/delete URLs use the primary
key (`/produits/3/`). To use another field — a slug, a name,
a reference — in the URLs:

```python
class ProduitResource(Resource):
    model = Produit
    lookup_field = "slug"   # doit être unique=True sur le modèle
```

This generates `/produits/<slug>/`, `/produits/<slug>/modifier/`, etc. The
library automatically derives:
- `lookup_url_kwarg` (URL parameter name, = `lookup_field` by default),
- `lookup_converter` (derived from the field type: `int` for `pk`,
  `slug` for a `SlugField`, `uuid` for a `UUIDField`, `str` otherwise —
  so `<slug:slug>` here). You can explicitly override them if needed.

**Important: `lookup_field` must be unique in the database** (`unique=True` on
the model field, or a primary key). Otherwise, two records
could share the same URL — the library emits a `UserWarning` at
startup if this is not the case (e.g. `name = models.CharField(...)` without
`unique=True` — this is probably what you are missing if you have
defined `lookup_field = "name"`):

```python
class Produit(models.Model):
    name = models.CharField(max_length=100, unique=True)   # <- ajouter unique=True
```

Without `unique=True`, looking up an object by this field can raise a
server error if two products share the same name. A dedicated `SlugField`
(`models.SlugField(unique=True)`, generated from the name via `slugify`) is
often a better choice than free text for a `lookup_field`,
as it is designed to be used in a URL (no spaces, accents,
or special characters).

All template tags (`djresource_list`, `djresource_detail`, etc.) and the
provided templates automatically adapt to the chosen `lookup_field` —
nothing else to change.

## Relationships (ForeignKey, OneToOneField, ManyToManyField)

Django handles relationships **natively** in the generated form, with
nothing extra to configure: just list the field in `fields`.

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

- **ForeignKey / OneToOneField**: becomes a dropdown (`<select>`)
  offering the related objects, displayed via their `__str__` — standard
  Django behavior.
- **ManyToManyField**: becomes a multi-select list. For a
  nicer widget (checkboxes, tag field...), use
  Level 3 (`{% djresource_form_data %}`) and build the field rendering
  yourself — the Django field (`form.tags`) remains available as is.
- **List/detail display**: `list_display` and the detail page
  automatically display an FK via its `__str__`, and an M2M (or a
  reverse relation) as a readable comma-separated list
  (e.g. `Électronique, Promo`).
- **Performance**: add FKs to `select_related` and M2Ms /
  reverse relations to `prefetch_related` to avoid N+1 queries
  when they appear in `list_display`:

```python
class ProduitResource(Resource):
    model = Produit
    list_display = ["nom", "categorie", "tags"]
    select_related = ["categorie", "fournisseur"]
    prefetch_related = ["tags"]
```

## File / image fields (FileField, ImageField)

For an `ImageField`, install Pillow (`pip install Pillow`) and
configure `MEDIA_URL`/`MEDIA_ROOT` in `settings.py`:

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

**Common pitfall (already fixed in the library):** an HTML form
containing a file field must have `enctype="multipart/form-data"`
on the `<form>` tag, otherwise the browser never sends the file —
Django receives an empty `request.FILES` and displays "This field is required."
even if a file was selected (often with no other visible error
: the request returns 200, it is just the invalid form being
redisplayed). All library form templates (`form.html`,
`form_partial.html`, in all 3 themes) now include it.

## Customizing the generated form (any CSS framework)

Regardless of the theme, full per-field control:

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

`widget_classes` takes precedence over `auto_form_css`/`theme` for the listed
fields (the others keep the theme styling). `widget_attrs` adds
any HTML attribute (data-*, aria-*, maxlength...) without touching
CSS classes. To fully disable automatic injection:

```python
class ProduitResource(Resource):
    model = Produit
    auto_form_css = False
```

## Adding business information to library pages

For the reverse — adding information to a page generated by djresource
rather than the other way around:

**`get_extra_context()`**: automatically injected into all generated views.

```python
class ProduitResource(Resource):
    model = Produit
    def get_extra_context(self, view):
        return {"valeur_stock_total": ...}
```

**Template blocks**: `list_top`, `list_bottom`, `list_header_actions`,
`form_top`, `form_bottom`, `detail_extra`, available in the full
pages of each theme.

```html
{% extends "djresource/list.html" %}
{% block list_top %}
<div class="alert alert-info">Stock total : {{ valeur_stock_total }} FCFA</div>
{% endblock %}
```

## ⚠️ Security — read before any deployment

1. **Authentication is required by default.** Generated CRUD views and
   injected components require a logged-in user. To make a resource public,
   opt in explicitly with `public = True`:

    ```python
   class ProduitResource(Resource):
       model = Produit
       public = True
   ```

2. **Scope every object access.** Override `scope_queryset(queryset, request)`
   to isolate tenants/owners. The resulting `get_queryset(request)` is used
   for list, detail, update, delete, and all injected contexts:

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

   The default `get_permissions()` returns `[LoginRequiredMixin]` (or `[]`
   when `public = True`). Overriding it replaces that policy: keep authentication
   in your custom mixins. Public access includes writes, not just reads.
   Authentication alone does not grant model-level or owner-level isolation.
   Scope does not restrict form relation choices; customize `get_form_class()`
   to restrict writable FK/M2M choices to authorized objects.

3. **No writable fields by default.** `fields = []` is the default. Explicitly
   list the fields allowed for writing. The legacy `fields = "__all__"` value
   remains supported with a `FieldsAllWarning` for compatibility, but should
   not be used for sensitive models.

4. **The `djresource_*` tags dynamically import** (`import_string`)
   the path passed as an argument. This path must **always** be a
   hard-coded string in the template, never built from
   user data. The library checks that the resolved class inherits
   from `Resource`, but this does not protect against a malicious
   dynamic path.

5. **Already covered, for information:**
    - Search (`?q=`): goes through the ORM (`Q(...)`), parameterized.
    - Sorting (`?sort=`): validated against a whitelist (`ordering_fields`).
    - `readonly_fields`: Django ignores the submitted POST value for a
      disabled field.
    - Non-existent `pk`: returns a clean 404 (`get_object_or_404`).
    - CSRF: `{% csrf_token %}` present in all forms, including
      partial templates.

6. **Demo project (`demo/`): do not use as is in production**
   (`SECRET_KEY` hard-coded, `DEBUG = True`, `ALLOWED_HOSTS = ["*"]`).

## Available configuration options

| Attribute | Role |
|---|---|
| `model` | Django model (required) |
| `fields` | Allowlist of writable form fields (empty by default; see Security §3) |
| `readonly_fields` | Fields displayed but not editable |
| `list_display` | Columns displayed in the list |
| `search_fields` | Fields covered by text search |
| `ordering_fields` | Fields on which click-to-sort is allowed |
| `list_filter` | Fields filterable via `?champ=valeur` (booleans, `choices` fields) |
| `paginate_by` | Number of objects per page (default: 20) |
| `select_related` / `prefetch_related` | Query optimization for relationships |
| `lookup_field` | Field used to identify the object in URLs (`"pk"` by default — see dedicated section) |
| `theme` | `"bootstrap"` (default) \| `"tailwind"` \| `"plain"` \| custom theme |
| `auto_form_css` | Auto-injection of theme CSS classes on the form |
| `widget_classes` / `widget_attrs` | Per-field CSS classes and HTML attributes, theme-independent |
| `template_list/detail/form/delete` | Override for a specific template |
| `get_extra_context(view)` | Injects business data into the context of all views |
| `get_list_context/get_form_context/get_detail_context` | Context computed outside the view (100% custom display) |
| `inlines` | Inline definitions; empty by default |
| `clean(instance, request)` | Validate before saving; raise ValidationError |
| `before_save(instance, request, is_new)` | Modify before saving |
| `after_save(instance, request, is_new)` | React after parent/M2M saving, before inlines |
| `before_delete(instance, request)` | Veto deletion with ValidationError |
| `after_delete(instance, request)` | React after deletion |
| `public` | Explicitly opt a resource out of default authentication |
| `get_permissions()` | Additional permission mixins; default is `LoginRequiredMixin` |
| `scope_queryset(queryset, request)` / `get_queryset(request)` | Request-aware object isolation |

## Available template tags (`{% load djresource_tags %}`)

| Tag | Renders HTML? | Usage |
|---|---|---|
| `djresource_list "chemin.Resource"` | Yes (chosen theme) | Inject the ready-made list component |
| `djresource_form "chemin.Resource" [lookup]` | Yes | Inject the ready-made form component |
| `djresource_detail "chemin.Resource" lookup` | Yes | Inject the ready-made detail component |
| `djresource_list_data "chemin.Resource" as v` | No | Raw list data, 100% free display |
| `djresource_form_data "chemin.Resource" [lookup] as v` | No | Raw form data |
| `djresource_detail_data "chemin.Resource" lookup as v` | No | Raw detail data |

`lookup` is the value of the resource's `lookup_field` — `produit.pk`
in the default case, or e.g. `produit.slug` if `lookup_field = "slug"`.

## Running the demo project (the provided one, produits/boutique)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

cd demo
python manage.py makemigrations produits
python manage.py migrate
python manage.py runserver
```

- `http://127.0.0.1:8000/produits/` — Generated CRUD (default theme).
- `http://127.0.0.1:8000/dashboard/` — custom page with the ready-made component injected.
- `http://127.0.0.1:8000/boutique/` — card-based e-commerce page, raw data, custom CSS.
- `http://127.0.0.1:8000/boutique/<pk>/` — product page with SEO meta tags + static info.

## Running the tests

```bash
python runtests.py
```

## Business hooks and inline formsets

Override `clean(instance, request)` to raise Django `ValidationError` and
redisplay the form. `before_save(instance, request, is_new)` can assign an owner;
`after_save(instance, request, is_new)` runs after the parent and M2M save.
`before_delete(instance, request)` may raise `ValidationError` to veto deletion;
`after_delete(instance, request)` runs only after deletion (the pk is then cleared).
Defaults are no-ops. Inline saving follows `after_save`, in the same transaction;
use `transaction.on_commit()` for external side effects.

```python
from django.forms import inlineformset_factory

class NoteInline:
    def get_formset_class(self, parent_model):
        return inlineformset_factory(parent_model, Note, fields=["text"], extra=1)

class ArticleWithNotesResource(Resource):
    model = Article
    fields = ["titre", "slug"]
    inlines = [NoteInline()]  # Note has a ForeignKey to Article
```

Formsets are validated before any write and saved after the parent receives its
pk. Each inline must have a distinct formset prefix. Built-in form templates
render management fields and errors. Custom forms must render `inline_formsets`.

## Django signals

```python
from django.dispatch import receiver
from djresource.signals import resource_post_save

@receiver(resource_post_save, sender=Article)
def article_saved(sender, instance, resource, **kwargs):
    pass  # react without subclassing Resource
```

`resource_pre_save` follows `before_save`; `resource_post_save` follows
`after_save` (parent/M2M saved, inlines not yet saved); `resource_post_delete`
follows `after_delete` (pk cleared). All pass `instance` and `resource`, with
`sender=resource.model`. Validation vetoes emit nothing. Receivers run
synchronously, exceptions propagate; use `transaction.on_commit()` for external
effects. Direct ORM writes and bulk operations do not emit these signals.

## HTMX (opt-in)

Set `htmx = True` on the Resource. Requests with `HX-Request: true` render
`list_partial`, `form_partial`, `detail_partial`, or `confirm_delete_partial`
instead of the complete page (all three themes). Invalid submissions also return
a partial; successful writes keep their normal redirect. Other requests are
unchanged. Permissions and CSRF remain enforced, and responses vary on
`HX-Request`. Include HTMX yourself, e.g. use `hx-get="/articles/"`
with `hx-target="#articles"` on a button. Partial selection uses the theme;
full-page template overrides are not reused as partials. Override the generated
view's `get_template_names()` for a custom partial.

## CSV export

Append `?export=csv` to the generated list URL, retaining `q`, filter fields,
`sort` and `dir` as needed. The export contains `list_display` columns and **all**
matching rows, ignoring pagination. It uses the list's permissions and owner
scope, with UTF-8 CSV quoting and a download filename. Relations are displayed
as in the HTML table. Spreadsheet formula-like strings are prefixed with `'`
for safety. The response is buffered in memory; override `export_csv(queryset)`
on the generated list view for very large datasets or a different format.

## Bulk actions (opt-in)

```python
class ArchiveArticles:
    name = "archive"
    label = "Archive selected articles"

    def run(self, queryset, request):
        queryset.update(actif=False)

class ArticleActionsResource(ArticleScopedResource):
    bulk_actions = [ArchiveArticles()]

    def has_bulk_action_permission(self, action, request):
        return request.user.has_perm("articles.change_article")
```

A dict with `name`, `label`, and a callable `run(queryset, request)` also works.
Names must be unique. `bulk_actions = []` preserves the existing list appearance
and rejects POST (405). All three themes and injected list components show
checkboxes and an action selector when actions are authorized. POST submits
`bulk_action` and repeated `selected` **primary keys**, even for slug-based URLs.
The form targets the generated list URL and retains search/filter/sort parameters.

List permissions run first; `has_bulk_action_permission()` adds per-action checks
(default: allow list users, **including anonymous users for public resources**).
Every selected object must be in the scoped, filtered queryset. Missing/foreign
objects reject the entire operation (403), malformed/empty selections or unknown
actions return 400. Actions run in a transaction; Django `ValidationError` rolls
back writes and displays an error. The selected queryset is not paginated.

`get_bulk_actions(request)` can supply request-specific actions. Put any extra
per-object authorization in `run()`. ORM bulk writes bypass Resource hooks and
signals, so implement that logic explicitly if needed. Use `transaction.on_commit`
for external effects. Rows are not locked against concurrent scope changes.
CSRF middleware must remain enabled in the host project.

## Django admin bridge

```python
from django.contrib import admin

admin.site.register(Article, ArticleResource().as_admin_class())
```

`as_admin_class()` returns an unregistered `ModelAdmin` subclass with copied
`list_display`, `search_fields`, and `list_filter`. You can subclass it before
registration. Django admin's staff/model permissions remain unchanged; Resource
`public`, owner scope, forms, hooks, and inlines are **not** transferred. Add
admin-specific isolation/business rules in that subclass. Values must satisfy
Django admin's checks (for example, direct M2M list columns are not supported).
