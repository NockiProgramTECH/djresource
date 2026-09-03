# Thèmes

DjResource fournit **3 thèmes de templates prêts à l'emploi**, choisis via
l'attribut `theme` sur votre ressource :

```python
class ProduitResource(Resource):
    model = Produit
    theme = "tailwind"   # "bootstrap" (défaut) | "tailwind" | "plain"
```

## Bootstrap (défaut)

```python
theme = "bootstrap"
```

- **Bootstrap 5.3** chargé via CDN.
- C'est le thème utilisé par défaut si `theme` n'est pas défini.
- Les formulaires reçoivent les classes `form-control`, `form-select`,
  `form-check-input`.

## Tailwind

```python
theme = "tailwind"
```

- **Tailwind CSS** chargé via le CDN `cdn.tailwindcss.com`.
- Idéal pour prototyper rapidement.
- Les formulaires reçoivent les classes utilitaires Tailwind.

!!! warning "Production"
    Pour la production, prévoyez un vrai pipeline de build Tailwind plutôt
    que le CDN de développement.

## Plain

```python
theme = "plain"
```

- HTML sémantique + une petite feuille de style fournie dans
  `djresource/static/djresource/css/djresource.css`.
- Classes neutres préfixées `djr-` (`djr-table`, `djr-btn`, `djr-form`,
  `djr-input`, …).
- C'est le point de départ idéal si vous voulez coder votre propre CSS :
  remplacez le fichier CSS, la structure HTML reste stable.

## Désactiver l'injection CSS sur le formulaire

Le formulaire auto-généré reçoit automatiquement les classes CSS du thème
choisi. Pour désactiver cette injection (CSS entièrement custom) :

```python
class ProduitResource(Resource):
    model = Produit
    auto_form_css = False
```

## Créer son propre thème

Copiez un dossier de thème existant, par exemple :

```bash
cp -r djresource/templates/djresource/plain/ monapp/templates/djresource/moncss/
```

Adaptez les templates, puis :

```python
class ProduitResource(Resource):
    model = Produit
    theme = "moncss"
```

La bibliothèque cherchera automatiquement `djresource/moncss/{kind}.html`
dans vos applications.

!!! note "Convention de nommage"
    Pour le thème **bootstrap** (défaut), les templates sont cherchés dans
    `djresource/templates/djresource/` directement. Pour tout autre thème,
    ils sont cherchés dans `djresource/templates/djresource/<theme>/`.
