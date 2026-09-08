from django.contrib.auth.mixins import LoginRequiredMixin

from djresource.resource import Resource

from .models import Article, Produit


class ProduitResource(Resource):
    model = Produit
    fields = ["nom", "prix", "stock", "actif"]
    list_display = ["nom", "prix", "stock", "actif"]
    search_fields = ["nom"]
    ordering_fields = ["nom", "prix", "stock"]
    theme = "tailwind"


class ArticleResource(Resource):
    """Resource dont les URLs utilisent le champ `slug` au lieu du pk."""

    model = Article
    fields = ["titre", "slug"]
    list_display = ["titre", "slug", "actif", "etat"]
    lookup_field = "slug"
    list_filter = ["actif", "etat"]
    theme = "tailwind"


class ArticleProtegeResource(ArticleResource):
    """
    Variante protégée par connexion : les vues générées (pages pleines ET
    partiels injectés) refusent les visiteurs anonymes.
    """

    def get_permissions(self):
        return [LoginRequiredMixin]
