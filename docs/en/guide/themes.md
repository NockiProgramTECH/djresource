# Themes

DjResource provides **3 ready-to-use template themes**, selected via
the `theme` attribute on your resource:

```python
class ProduitResource(Resource):
    model = Produit
    theme = "tailwind"   # "bootstrap" (défaut) | "tailwind" | "plain"
```

## Bootstrap (default)

```python
theme = "bootstrap"
```

- **Bootstrap 5.3** loaded via CDN.
- This is the theme used by default if `theme` is not set.
- Forms receive the `form-control`, `form-select`,
  `form-check-input` classes.

## Tailwind

```python
theme = "tailwind"
```

- **Tailwind CSS** loaded via the `cdn.tailwindcss.com` CDN.
- Ideal for rapid prototyping.
- Forms receive the Tailwind utility classes.

!!! warning "Production"
    For production, plan on using a real Tailwind build pipeline rather
    than the development CDN.

## Plain

```python
theme = "plain"
```

- Semantic HTML + a small stylesheet shipped in
  `djresource/static/djresource/css/djresource.css`.
- Neutral classes prefixed with `djr-` (`djr-table`, `djr-btn`, `djr-form`,
  `djr-input`, …).
- This is the ideal starting point if you want to write your own CSS:
  replace the CSS file, the HTML structure stays stable.

## Disable CSS injection on the form

The auto-generated form automatically receives the CSS classes of the
chosen theme. To disable this injection (fully custom CSS):

```python
class ProduitResource(Resource):
    model = Produit
    auto_form_css = False
```

## Create your own theme

Copy an existing theme folder, for example:

```bash
cp -r djresource/templates/djresource/plain/ monapp/templates/djresource/moncss/
```

Adapt the templates, then:

```python
class ProduitResource(Resource):
    model = Produit
    theme = "moncss"
```

The library will automatically look for `djresource/moncss/{kind}.html`
in your applications.

!!! note "Naming convention"
    For the **bootstrap** theme (default), templates are looked up directly in
    `djresource/templates/djresource/`. For any other theme,
    they are looked up in `djresource/templates/djresource/<theme>/`.
