from django.urls import include, path

from .resources import ArticleResource, ProduitResource

urlpatterns = [
    path("produits/", include(ProduitResource().urls())),
    path("articles/", include(ArticleResource().urls())),
]
