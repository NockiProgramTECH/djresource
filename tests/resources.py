from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from djresource.resource import Resource

from .models import Article, Produit


class ProduitResource(Resource):
    model = Produit
    public = True
    fields = ["nom", "prix", "stock", "actif"]
    list_display = ["nom", "prix", "stock", "actif"]
    search_fields = ["nom"]
    ordering_fields = ["nom", "prix", "stock"]
    theme = "tailwind"


class ArticleResource(Resource):
    """Resource dont les URLs utilisent le champ `slug` au lieu du pk."""

    model = Article
    public = True
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


class ArticleScopedResource(ArticleResource):
    """Resource used to verify request-aware object isolation."""

    def scope_queryset(self, queryset, request=None):
        return queryset.filter(owner=request.user)

    def before_save(self, instance, request, is_new):
        if is_new:
            instance.owner = request.user


class ArticleDefaultProtectedResource(Resource):
    model = Article


class ArticleBusinessProtectedResource(ArticleResource):
    def get_permissions(self):
        return [LoginRequiredMixin, UserPassesTestMixin]

    def test_func(self, request):
        return request.user.username == "allowed"


class ArticleNoteInline:
    def get_formset_class(self, parent_model):
        from django.forms import inlineformset_factory
        from .models import ArticleNote

        return inlineformset_factory(parent_model, ArticleNote, fields=["text"], extra=1)


class ArticleInlineResource(ArticleScopedResource):
    inlines = [ArticleNoteInline()]
