"""
Tests d'intégration qui valident que le CRUD généré par djresource
fonctionne de bout en bout sur un modèle de test.
"""
import warnings

from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse

from djresource.resource import FieldsAllWarning, Resource

from .models import Article, Produit
from .resources import ArticleProtegeResource, ArticleResource


class ProduitToutChampsResource(Resource):
    """Resource laissée avec le défaut `fields = "__all__"` (à éviter)."""

    model = Produit


class FieldsExplicitesTests(TestCase):
    """
    SÉCURITÉ : `fields = "__all__"` (défaut) expose tous les champs du
    modèle dans le formulaire (mass assignment). Un avertissement doit être
    émis à l'instanciation pour inciter à déclarer les champs explicitement.
    """

    def test_fields_all_emmet_un_avertissement(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ProduitToutChampsResource()
        self.assertTrue(
            any(issubclass(w.category, FieldsAllWarning) for w in caught),
            "fields='__all__' doit émettre un FieldsAllWarning",
        )

    def test_fields_explicites_pas_d_avertissement(self):
        from .resources import ProduitResource  # import local pour la lisibilité

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ProduitResource()
        self.assertFalse(
            any(issubclass(w.category, FieldsAllWarning) for w in caught),
            "fields explicites ne doit PAS émettre de FieldsAllWarning",
        )


class ArticleSlugLookupTests(TestCase):
    """
    Valide le paramètre `lookup_field` de Resource : les URLs de détail /
    modification / suppression utilisent un autre champ que le pk (ici
    "slug" sur le modèle Article).
    """

    def setUp(self):
        self.article = Article.objects.create(titre="Riz local", slug="riz-local")

    def test_pattern_url_du_slug(self):
        self.assertEqual(ArticleResource().get_lookup_url(), "<slug:slug>")

    def test_detail_par_slug(self):
        url = reverse("article_detail", args=["riz-local"])
        self.assertEqual(url, "/articles/riz-local/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riz local")

    def test_modification_par_slug(self):
        response = self.client.post(
            reverse("article_update", args=["riz-local"]),
            {"titre": "Riz local (promo)", "slug": "riz-local"},
        )
        self.assertRedirects(response, reverse("article_list"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.titre, "Riz local (promo)")

    def test_suppression_par_slug(self):
        response = self.client.post(reverse("article_delete", args=["riz-local"]))
        self.assertRedirects(response, reverse("article_list"))
        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())

    def test_slug_inconnu_retourne_404(self):
        response = self.client.get(reverse("article_detail", args=["introuvable"]))
        self.assertEqual(response.status_code, 404)

    def test_valeur_lookup(self):
        self.assertEqual(ArticleResource().get_lookup_value(self.article), "riz-local")


class PartialPermissionsTests(TestCase):
    """
    SÉCURITÉ : les partiels injectés (`get_list_context`, `get_form_context`,
    `get_detail_context`) doivent appliquer les permissions de la Resource
    (`get_permissions()`), comme le font les pages pleine page via dispatch().
    Un visiteur anonyme sur une Resource protégée par LoginRequiredMixin ne
    doit PAS pouvoir obtenir le contexte d'un composant injecté.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.resource = ArticleProtegeResource()
        self.article = Article.objects.create(titre="Riz local", slug="riz-local")
        self.user = User.objects.create_user(username="alice", password="secret")

    def _request(self, user):
        request = self.factory.get("/")
        # RequestFactory ne passe pas par AuthenticationMiddleware.
        request.user = user
        return request

    def test_liste_partielle_refuse_anonyme(self):
        with self.assertRaises(PermissionDenied):
            self.resource.get_list_context(self._request(AnonymousUser()))

    def test_liste_partielle_autorise_connecte(self):
        context = self.resource.get_list_context(self._request(self.user))
        self.assertIn("object_list", context)

    def test_detail_partiel_refuse_anonyme(self):
        with self.assertRaises(PermissionDenied):
            self.resource.get_detail_context(self._request(AnonymousUser()), "riz-local")

    def test_detail_partiel_autorise_connecte(self):
        context = self.resource.get_detail_context(self._request(self.user), "riz-local")
        self.assertEqual(context["object"].slug, "riz-local")

    def test_formulaire_partiel_refuse_anonyme(self):
        with self.assertRaises(PermissionDenied):
            self.resource.get_form_context(self._request(AnonymousUser()))

    def test_formulaire_partiel_autorise_connecte(self):
        context = self.resource.get_form_context(self._request(self.user))
        self.assertIn("form", context)


class ProduitCrudTests(TestCase):
    def setUp(self):
        self.produit = Produit.objects.create(nom="Riz local", prix=15000, stock=50)

    def test_liste_produits_affiche_les_objets(self):
        response = self.client.get(reverse("produit_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riz local")

    def test_creation_produit(self):
        response = self.client.post(reverse("produit_create"), {
            "nom": "Huile 1L",
            "prix": 2500,
            "stock": 30,
            "actif": True,
        })
        self.assertRedirects(response, reverse("produit_list"))
        self.assertTrue(Produit.objects.filter(nom="Huile 1L").exists())

    def test_modification_produit(self):
        response = self.client.post(
            reverse("produit_update", args=[self.produit.pk]),
            {"nom": "Riz local (promo)", "prix": 12000, "stock": 50, "actif": True},
        )
        self.assertRedirects(response, reverse("produit_list"))
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.nom, "Riz local (promo)")

    def test_suppression_produit(self):
        response = self.client.post(reverse("produit_delete", args=[self.produit.pk]))
        self.assertRedirects(response, reverse("produit_list"))
        self.assertFalse(Produit.objects.filter(pk=self.produit.pk).exists())

    def test_recherche_filtre_les_resultats(self):
        Produit.objects.create(nom="Savon", prix=500, stock=100)
        response = self.client.get(reverse("produit_list"), {"q": "riz"})
        self.assertContains(response, "Riz local")
        self.assertNotContains(response, "Savon")

    def test_detail_affiche_l_objet(self):
        response = self.client.get(reverse("produit_detail", args=[self.produit.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riz local")
